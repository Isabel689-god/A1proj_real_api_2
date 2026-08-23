"""案例库检索服务 — 结构化过滤 + 加权打分。

检索优先级：
1. 同设备 + 同故障代码 → 最高权重
2. 同故障代码不同设备 → 中等权重
3. 关键词语义匹配 → 基础权重
4. 超过阈值 → 直接复用案例；未超过 → 走图谱推理
"""

from __future__ import annotations

import re
from typing import Any

from app.db import get_session, MaintenanceRecord
from sqlalchemy.orm import defer


# 复用阈值：超过此分认为案例可直接复用
REUSE_THRESHOLD = 0.70

# 权重配置
WEIGHT_SAME_DEVICE_AND_CODE = 30   # 同设备 + 同代码
WEIGHT_SAME_CODE = 20              # 同代码
WEIGHT_SAME_DEVICE = 15            # 同设备
WEIGHT_SAME_TYPE = 10              # 同故障类型
WEIGHT_KEYWORD_HIT = 3             # 每个关键词命中

# 分档置信度（matched 判定按信号强度分档，不再堆分数归一化）
CONF_SAME_DEVICE_AND_CODE = 0.95   # 同设备+同代码：最强信号，直接复用
CONF_SAME_CODE = 0.85              # 同代码（跨设备）：复用 + 手册交叉验证
CONF_SAME_DEVICE = 0.60            # 仅同设备：不足复用
CONF_KEYWORD_MAX = 0.50            # 关键词弱匹配置信度上限


def _extract_fault_code(text: str) -> str:
    """从文本中提取报警代码（数字 2-6 位）。"""
    m = re.search(r"(?:报警|告警|故障码|故障代码|代码)\s*[:：#]?\s*([A-Za-z]?\d{2,6})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b([A-Za-z]?\d{2,6})\b", text)
    return m.group(1).upper() if m else ""


def _tokenize(text: str) -> set[str]:
    """中文分词 + 英文数字提取。"""
    words = set(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower()))
    stop = {"步骤", "检查", "确认", "操作", "处理", "进行", "完成", "原因", "方法", "分析", "系统", "设备"}
    return words - stop


def _keyword_score(query_tokens: set[str], doc_text: str) -> int:
    """关键词命中评分。"""
    doc_lower = doc_text.lower()
    score = 0
    for token in query_tokens:
        if token and token in doc_lower:
            score += WEIGHT_KEYWORD_HIT
    # 连续 bigram 加成
    bigrams = set()
    text = "".join(query_tokens)
    for i in range(len(text) - 1):
        bigram = text[i:i+2]
        if bigram.strip():
            bigrams.add(bigram)
    consecutive = sum(1 for b in bigrams if b in doc_lower)
    if consecutive >= 3:
        score += 6
    return score


def _device_match(case_device: str, query_device: str) -> bool:
    """模糊设备匹配：型号关键词互相包含。"""
    if not case_device or not query_device:
        return False
    cd = case_device.lower().replace("-", "").replace(" ", "")
    qd = query_device.lower().replace("-", "").replace(" ", "")
    # 任一方向子串匹配
    return cd in qd or qd in cd or any(
        part in qd for part in cd.split("/") if len(part) >= 3
    )


class CaseSearchService:
    """案例库优先检索服务。"""

    def search(
        self,
        question: str,
        device_model: str | None = None,
        fault_code: str | None = None,
        fault_type: str | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """检索案例库，返回命中结果 + 是否可复用。

        返回格式：
        {
            "matched": bool,           # 是否有高置信度命中
            "confidence": float,       # 最高置信度 (0-1)
            "cases": [                 # 匹配案例列表
                {
                    "record_id": str,
                    "device_model": str,
                    "fault_type": str,
                    "fault_cause": str,
                    "description": str,
                    "solution": str,
                    "score": float,     # 加权得分
                    "match_reason": str,
                }
            ],
        }
        """
        db = get_session()
        try:
            # ── 第一阶段：结构化过滤 ──
            records = self._structured_filter(
                db, question, device_model, fault_code, fault_type
            )

            if not records:
                return {"matched": False, "confidence": 0.0, "cases": []}

            # ── 第二阶段：加权打分 ──
            query_tokens = _tokenize(question)
            extracted_code = fault_code or _extract_fault_code(question)

            scored = []
            for rec in records:
                score, reason = self._score_case(
                    rec, query_tokens, extracted_code, device_model or "", fault_type or ""
                )
                if score > 0:
                    scored.append({
                        "record_id": rec.record_id,
                        "device_model": rec.device_model or "",
                        "fault_type": rec.fault_type or "",
                        "fault_cause": rec.fault_cause or "",
                        "description": rec.description or "",
                        "solution": rec.solution or "",
                        "score": score,
                        "match_reason": reason,
                    })

            scored.sort(key=lambda x: x["score"], reverse=True)
            best = scored[:top_k]

            if not best:
                return {"matched": False, "confidence": 0.0, "cases": []}

            # 分档置信度：按匹配信号强度判定，同代码即达阈值
            confidence = self._confidence(best[0])
            matched = confidence >= REUSE_THRESHOLD

            return {
                "matched": matched,
                "confidence": confidence,
                "cases": best,
            }
        finally:
            db.close()

    def _structured_filter(
        self, db, question: str, device_model: str | None,
        fault_code: str | None, fault_type: str | None,
    ) -> list:
        """SQL 结构化过滤：优先同设备同代码，逐步放宽。"""
        results: dict[str, Any] = {}  # record_id → record

        if not fault_code:
            fault_code = _extract_fault_code(question)

        # 1. 同故障代码（最精确）
        if fault_code:
            records = db.query(MaintenanceRecord).filter(
                MaintenanceRecord.fault_type.contains(fault_code)
            ).limit(20).all()
            for r in records:
                results[r.record_id] = r

        # 2. 同设备型号
        if device_model:
            records = db.query(MaintenanceRecord).filter(
                MaintenanceRecord.device_model.contains(device_model[:20])
            ).limit(20).all()
            for r in records:
                if r.record_id not in results:
                    results[r.record_id] = r

        # 3. 同故障类型关键词
        if fault_type:
            records = db.query(MaintenanceRecord).filter(
                MaintenanceRecord.fault_type.contains(fault_type[:20])
            ).limit(20).all()
            for r in records:
                if r.record_id not in results:
                    results[r.record_id] = r

        # 4. 如果以上都没命中，取最近 30 条做关键词兜底
        if not results:
            records = db.query(MaintenanceRecord).options(defer(MaintenanceRecord.report_data)).order_by(
                MaintenanceRecord.created_at.desc()
            ).limit(30).all()
            for r in records:
                results[r.record_id] = r

        return list(results.values())

    def _score_case(
        self,
        rec,
        query_tokens: set[str],
        fault_code: str,
        device_model: str,
        fault_type: str,
    ) -> tuple[int, str]:
        """对单个案例加权打分。"""
        score = 0
        reasons = []

        # 同设备 + 同代码
        device_hit = _device_match(rec.device_model or "", device_model)
        code_hit = fault_code and fault_code.lower() in (rec.fault_type or "").lower()

        if device_hit and code_hit:
            score += WEIGHT_SAME_DEVICE_AND_CODE
            reasons.append("同设备+同代码")
        elif code_hit:
            score += WEIGHT_SAME_CODE
            reasons.append("同故障代码")
        elif device_hit:
            score += WEIGHT_SAME_DEVICE
            reasons.append("同设备")

        # 同故障类型关键词
        if fault_type and fault_type in (rec.fault_type or ""):
            score += WEIGHT_SAME_TYPE
            reasons.append("同故障类型")

        # 关键词命中
        combined = f"{rec.description or ''} {rec.solution or ''} {rec.fault_cause or ''}"
        kw = _keyword_score(query_tokens, combined)
        score += kw
        if kw >= 9:
            reasons.append(f"关键词匹配({kw}分)")

        reason = " | ".join(reasons) if reasons else "关键词弱匹配"
        return score, reason

    def _confidence(self, case: dict) -> float:
        """分档置信度：按匹配信号强度直接判定，而非堆分数归一化。

        同设备+同代码 → 0.95 直接复用；同代码 → 0.85 复用+交叉验证；
        仅同设备 → 0.60 不足复用；关键词弱匹配 → 按分数归一化，上限 0.50。
        """
        reason = case.get("match_reason", "")
        score = case.get("score", 0)
        if "同设备+同代码" in reason:
            return CONF_SAME_DEVICE_AND_CODE
        if "同故障代码" in reason:
            return CONF_SAME_CODE
        if "同设备" in reason:
            return CONF_SAME_DEVICE
        return min(CONF_KEYWORD_MAX, round(score / 60, 4))

    def format_case_context(self, case: dict) -> str:
        """将匹配案例格式化为 LLM 上下文。"""
        parts = [
            f"【历史案例】{case['record_id']}",
            f"设备型号：{case['device_model']}",
            f"故障类型：{case['fault_type']}",
            f"故障原因：{case['fault_cause'] or '未记录'}",
            f"故障描述：{case['description'] or '未记录'}",
            f"维修方案：{case['solution'] or '未记录'}",
            f"匹配度：{case['score']}分 | {case['match_reason']}",
        ]
        return "\n".join(parts)


case_service = CaseSearchService()
