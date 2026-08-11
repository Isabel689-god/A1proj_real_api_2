"""SOP 版本管理服务 — MySQL 持久化，与聊天记录同库存储。"""
from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from app.db import get_session
from app.db.models import SopVersion


_STAGE_ORDER = {
    "fault_confirmation": 10,
    "safety_preparation": 20,
    "initial_check": 30,
    "electrical_check": 40,
    "parameter_check": 50,
    "repair_or_replace": 60,
    "reset_recovery": 70,
    "validation": 80,
    "record": 90,
}

_NOTE_TYPES = {"operation_standard", "safety_requirement", "warning"}


def _row_to_dict(row: SopVersion) -> dict:
    """SopVersion ORM 对象 → dict（与旧 JSON 格式兼容）。"""
    return {
        "version": row.version,
        "sop_id": row.sop_id,
        "parent_sop_id": row.parent_sop_id,
        "session_id": row.session_id,
        "user_id": row.user_id,
        "question": row.question,
        "answer_preview": row.answer_preview,
        "steps": json.loads(row.steps) if row.steps else [],
        "notes": json.loads(row.notes) if row.notes else [],
        "issue_fingerprint": row.issue_fingerprint,
        "fault_code": row.fault_code,
        "device_model": row.device_model,
        "sop_status": row.sop_status,
        "classification": json.loads(row.classification) if row.classification else {},
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "trace_id": row.trace_id,
    }


class SopService:
    """SOP 版本管理与迭代（MySQL 持久化）。"""

    # ── 公开 API ──────────────────────────────────────────────

    def get_versions(self, session_id: str, retry: int = 0) -> list[dict]:
        """获取某会话的所有 SOP 版本（按 version 升序）。"""
        db = get_session()
        try:
            rows = (
                db.query(SopVersion)
                .filter(SopVersion.session_id == session_id)
                .order_by(SopVersion.version)
                .all()
            )
            return [_row_to_dict(r) for r in rows]
        except Exception:
            if retry < 2:
                import time as _time
                _time.sleep(0.1 * (retry + 1))
                return self.get_versions(session_id, retry=retry + 1)
            return []
        finally:
            db.close()

    def get_latest(self, session_id: str) -> dict | None:
        """获取最新版本。"""
        db = get_session()
        try:
            row = (
                db.query(SopVersion)
                .filter(SopVersion.session_id == session_id)
                .order_by(SopVersion.version.desc())
                .first()
            )
            return _row_to_dict(row) if row else None
        finally:
            db.close()

    def save_version(
        self,
        session_id: str,
        user_id: str,
        question: str,
        steps: list[dict],
        answer_preview: str = "",
        trace_id: str = "",
    ) -> dict:
        """保存新版本。同故障且已有步骤时拒绝覆盖（硬守卫）。"""
        versions = self.get_versions(session_id)
        latest = versions[-1] if versions else None

        # 硬守卫：已有非空步骤 → 绝不覆盖
        if latest and latest.get("steps"):
            latest["updated_at"] = datetime.now(timezone.utc).isoformat()
            return latest

        issue = self._classify_issue(session_id, question, answer_preview, latest)
        same_issue = not latest or issue["decision"] == "same"
        base_steps = latest.get("steps", []) if latest and same_issue else []
        base_notes = latest.get("notes", []) if latest and same_issue else []
        cleaned_steps, notes = self._split_steps_and_notes(steps)
        if same_issue and base_steps:
            merged_steps = list(base_steps)
        else:
            merged_steps = self._merge_steps(base_steps, cleaned_steps)
        old_statuses = []
        if latest and same_issue:
            for s in latest.get("steps", []):
                old_statuses.append((s.get("step_status", "pending"), s.get("step_note", "")))
        for i, s in enumerate(merged_steps):
            if i < len(old_statuses):
                s["step_status"], s["step_note"] = old_statuses[i]
            elif "step_status" not in s:
                s["step_status"] = "pending"
        merged_notes = self._merge_notes(base_notes, notes)
        version = len(versions) + 1

        db = get_session()
        try:
            record = SopVersion(
                session_id=session_id,
                user_id=user_id,
                version=version,
                sop_id=issue["sop_id"],
                parent_sop_id=latest.get("sop_id") if latest and not same_issue else "",
                question=question[:100],
                answer_preview=answer_preview[:200],
                steps=json.dumps(merged_steps, ensure_ascii=False),
                notes=json.dumps(merged_notes, ensure_ascii=False),
                issue_fingerprint=issue["fingerprint"],
                fault_code=issue["features"].get("fault_code", ""),
                device_model=issue["features"].get("device_model", ""),
                sop_status="needs_confirmation" if issue["decision"] == "ambiguous" else "active",
                classification=json.dumps(issue, ensure_ascii=False),
                trace_id=trace_id or f"{session_id}:v{version}",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return _row_to_dict(record)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_step_status(self, session_id: str, step_index: int, status: str, note: str = "") -> dict | None:
        """更新单步状态。返回更新后的最新版本 dict，SOP 不存在时返回 None。"""
        db = get_session()
        try:
            row = (
                db.query(SopVersion)
                .filter(SopVersion.session_id == session_id)
                .order_by(SopVersion.version.desc())
                .first()
            )
            if not row:
                return None
            steps = json.loads(row.steps) if row.steps else []
            if step_index < 1 or step_index > len(steps):
                return None
            steps[step_index - 1]["step_status"] = status
            if note:
                steps[step_index - 1]["step_note"] = note
            row.steps = json.dumps(steps, ensure_ascii=False)
            db.commit()
            db.refresh(row)
            return _row_to_dict(row)
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()

    def batch_update_steps(self, session_id: str, updates: list[tuple[int, str, str]]) -> dict | None:
        """批量更新步骤状态，一次写入。SOP 不存在时返回 None。"""
        if not updates:
            return None
        db = get_session()
        try:
            row = (
                db.query(SopVersion)
                .filter(SopVersion.session_id == session_id)
                .order_by(SopVersion.version.desc())
                .first()
            )
            if not row:
                return None
            steps = json.loads(row.steps) if row.steps else []
            for step_index, status, note in updates:
                if 1 <= step_index <= len(steps):
                    steps[step_index - 1]["step_status"] = status
                    if note:
                        steps[step_index - 1]["step_note"] = note
            row.steps = json.dumps(steps, ensure_ascii=False)
            db.commit()
            db.refresh(row)
            return _row_to_dict(row)
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()

    def get_sop_state(self, session_id: str) -> dict:
        """获取当前 SOP 完整状态（供 Agent 工具查询）。"""
        latest = self.get_latest(session_id)
        if not latest:
            return {"exists": False, "sop_id": ""}
        steps = []
        for s in latest.get("steps", []):
            steps.append({
                "index": s.get("step_order", 0),
                "title": s.get("title", ""),
                "desc": s.get("desc", ""),
                "status": s.get("step_status", "pending"),
                "note": s.get("step_note", ""),
            })
        return {
            "exists": True,
            "sop_id": latest.get("sop_id", ""),
            "session_id": session_id,
            "fault": latest.get("question", ""),
            "device_model": latest.get("device_model", ""),
            "current_step": latest.get("current_step", 1),
            "total_steps": len(steps),
            "all_done": all(s["status"] == "done" for s in steps),
            "steps": steps,
        }

    def get_iteration_context(self, session_id: str) -> str:
        """生成注入 Agent 的上下文：上一版 SOP 步骤状态。"""
        latest = self.get_latest(session_id)
        if not latest or not latest.get("steps"):
            return ""
        lines = ["【上轮已生成的 SOP（请基于此增量优化，不要删除已有步骤）】"]
        for i, s in enumerate(latest["steps"], 1):
            status = s.get("step_status", "pending")
            icon = {"done": "✅", "in_progress": "🔄", "pending": "⬜"}.get(status, "⬜")
            lines.append(f"{icon} {i}. [{s.get('title','')}] {s.get('desc','')} ({status})")
        notes = latest.get("notes") or []
        if notes:
            lines.append("【操作规范与安全要求（不是普通步骤，不要编号到步骤列表）】")
            for n in notes:
                lines.append(f"- {n.get('title', '')}: {n.get('content', '')}")
        return "\n".join(lines)

    # ── 内部方法（与旧实现一致） ──────────────────────────────

    def _merge_steps(self, old_steps: list[dict], new_steps: list[dict]) -> list[dict]:
        if not old_steps:
            return self._validate_steps([self._normalize_step(s, i + 1) for i, s in enumerate(new_steps)])
        if not new_steps:
            return self._validate_steps([self._normalize_step(s, i + 1) for i, s in enumerate(old_steps)])
        merged = [self._normalize_step(s, i + 1) for i, s in enumerate(old_steps)]
        for raw in new_steps:
            step = self._normalize_step(raw, len(merged) + 1)
            idx = self._find_related_step(merged, step)
            if idx >= 0:
                old = merged[idx]
                desc = step.get("desc", "")
                if desc and desc not in old.get("desc", ""):
                    old["desc"] = f"{old.get('desc', '')}\n补充：{desc}".strip()
                old["title"] = old.get("title") or step.get("title")
                old["updated"] = True
            else:
                merged.append(step)
        return self._validate_steps(merged)[:12]

    def _normalize_step(self, step: dict, index: int) -> dict:
        title = str(step.get("title") or step.get("step_title") or "").strip()
        desc = str(step.get("desc") or step.get("description") or "").strip()
        title = re.sub(r"^(步骤\s*)?\d+\s*[\.\、\）\):-]?\s*", "", title).strip()
        if not title or title in {"步骤", "操作"}:
            title = self._title_from_desc(desc) or f"检修步骤 {index}"
        step_type = step.get("step_type") or self._infer_step_type(title, desc)
        return {
            **step,
            "step_order": index,
            "step_title": title[:40],
            "title": title[:40],
            "step_description": desc[:500],
            "desc": desc[:500],
            "step_type": step_type,
            "safety_level": step.get("safety_level") or ("high" if step_type == "safety_preparation" else "normal"),
            "tools": step.get("tools", []),
            "expected_result": step.get("expected_result", ""),
            "warning": step.get("warning", ""),
            "source_reference": step.get("source_reference", ""),
        }

    def _split_steps_and_notes(self, steps: list[dict]) -> tuple[list[dict], list[dict]]:
        clean_steps: list[dict] = []
        notes: list[dict] = []
        for raw in steps:
            title = str(raw.get("title") or raw.get("step_title") or "")
            desc = str(raw.get("desc") or raw.get("description") or "")
            step_type = raw.get("step_type") or self._infer_step_type(title, desc)
            if step_type in _NOTE_TYPES:
                notes.append({
                    "type": step_type,
                    "title": re.sub(r"^(步骤\s*)?\d+\s*[\.\、\）\):-]?\s*", "", title).strip() or "操作规范与注意事项",
                    "content": desc[:500],
                })
            else:
                clean_steps.append({**raw, "step_type": step_type})
        return clean_steps, notes

    def _merge_notes(self, old_notes: list[dict], new_notes: list[dict]) -> list[dict]:
        merged = list(old_notes)
        seen = {self._fingerprint_text(f"{n.get('title', '')} {n.get('content', '')}") for n in merged}
        for note in new_notes:
            fp = self._fingerprint_text(f"{note.get('title', '')} {note.get('content', '')}")
            if fp and fp not in seen:
                merged.append(note)
                seen.add(fp)
        return merged[:8]

    def _validate_steps(self, steps: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        seen = set()
        for i, raw in enumerate(steps, 1):
            step = self._normalize_step(raw, i)
            if step["step_type"] in _NOTE_TYPES:
                continue
            fp = self._fingerprint_text(f"{step['title']} {step['desc']}")
            if fp in seen:
                continue
            seen.add(fp)
            filtered.append(step)
        filtered.sort(key=lambda s: s.get("step_order", 999))
        for order, step in enumerate(filtered, 1):
            step["step_order"] = order
        return filtered

    def _title_from_desc(self, desc: str) -> str:
        text = re.split(r"[。；;，,\n]", desc.strip(), 1)[0]
        text = re.sub(r"^(先|然后|再|最后|并|进行|检查|确认)", "", text).strip()
        return text[:24]

    def _infer_step_type(self, title: str, desc: str) -> str:
        text = f"{title} {desc}"
        if re.search(r"绝缘要求|安装偏差|防护要求|注意事项", text):
            return "operation_standard"
        if re.search(r"断电|上锁|挂牌|防护|放电|安全|急停", text):
            return "safety_preparation"
        if re.search(r"现象|报警|故障码|记录代码|确认故障", text):
            return "fault_confirmation"
        if re.search(r"电气|线缆|接线|端子|电源|电压|电流|编码器线", text):
            return "electrical_check"
        if re.search(r"参数|配置|设定|备份|PLC|梯形图", text, re.IGNORECASE):
            return "parameter_check"
        if re.search(r"更换|拆装|维修|修复|清洁|调整|电池|部件", text):
            return "repair_or_replace"
        if re.search(r"复位|回零|恢复|清除报警|重启", text):
            return "reset_recovery"
        if re.search(r"验证|测试|试运行|空运行|负载运行|确认恢复", text):
            return "validation"
        if re.search(r"记录|归档|结单|填写", text):
            return "record"
        return "initial_check"

    def _find_related_step(self, steps: list[dict], candidate: dict) -> int:
        def tokens(text: str) -> set[str]:
            words = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}", text.lower())
            stop = {"步骤", "检查", "确认", "操作", "处理", "进行", "完成"}
            result = {w for w in words if w not in stop}
            for word in words:
                if re.fullmatch(r"[\u4e00-\u9fff]{3,}", word):
                    result.update(word[i:i + 2] for i in range(len(word) - 1))
            return result

        cand = tokens(f"{candidate.get('title', '')} {candidate.get('desc', '')}")
        if not cand:
            return -1
        best_idx, best_score = -1, 0.0
        best_overlap = 0
        for i, step in enumerate(steps):
            current = tokens(f"{step.get('title', '')} {step.get('desc', '')}")
            if not current:
                continue
            overlap = len(cand & current)
            score = overlap / max(len(cand | current), 1)
            if score > best_score:
                best_idx, best_score = i, score
                best_overlap = overlap
        return best_idx if best_score >= 0.12 or best_overlap >= 3 else -1

    def _classify_issue(self, session_id: str, question: str, answer: str, latest: dict | None) -> dict:
        features = self._extract_issue_features(question, answer)
        fingerprint = self._issue_fingerprint(features)
        sop_id = f"sop_{hashlib.sha1(fingerprint.encode('utf-8')).hexdigest()[:12]}"
        if not latest:
            return {
                "decision": "new", "confidence": 1.0, "reason": "当前会话尚无 SOP",
                "fingerprint": fingerprint, "sop_id": sop_id, "features": features,
                "needs_confirmation": False,
            }
        prev = latest.get("classification", {}).get("features") or self._extract_issue_features(
            latest.get("question", ""), latest.get("answer_preview", ""))
        explicit_new = bool(re.search(r"另一个|另外|新故障|换个|不是这个|其他报警", question))
        if prev.get("fault_code") and features.get("fault_code") and prev["fault_code"] != features["fault_code"]:
            decision, confidence, reason = "new", 0.96, "故障代码变化"
        elif explicit_new and self._similarity(prev, features) < 0.45:
            decision, confidence, reason = "new", 0.84, "用户明确切换问题且语义差异较大"
        elif re.search(r"已(执行|完成|做完|修好|修复|排查|弄好|搞定)|维修成功|寻参成功|步骤.*(完成|做完|OK|ok)|第\s*\d+\s*步|不太会|怎么做|怎么操作|详细说|讲一下|说明一下|解释一下|上述|刚才|继续|然后|接下来|全部完成|所有步骤", question):
            decision, confidence, reason = "same", 0.9, "用户确认/追问，同一故障"
            sop_id = latest.get("sop_id") or sop_id
            fingerprint = latest.get("issue_fingerprint") or fingerprint
        elif latest and latest.get("steps") and not explicit_new:
            decision, confidence, reason = "same", 0.8, "会话已有SOP，默认同一故障"
            sop_id = latest.get("sop_id") or sop_id
            fingerprint = latest.get("issue_fingerprint") or fingerprint
        else:
            sim = self._similarity(prev, features)
            if sim >= 0.42:
                decision, confidence, reason = "same", round(max(sim, 0.68), 2), "设备/故障上下文连续"
                sop_id = latest.get("sop_id") or sop_id
                fingerprint = latest.get("issue_fingerprint") or fingerprint
            elif prev.get("fault_code") and not features.get("fault_code") and re.search(r"这个|上述|刚才|继续|然后|复位|更换|验证|参数", question):
                decision, confidence, reason = "same", 0.62, "追问语义指向上一检修任务"
                sop_id = latest.get("sop_id") or sop_id
                fingerprint = latest.get("issue_fingerprint") or fingerprint
            elif re.search(r"还有.*报警|另.*报警", question) and not features.get("fault_code") and not features.get("component"):
                decision, confidence, reason = "ambiguous", 0.35, "缺少报警代码或设备信息，需要用户确认"
                sop_id = latest.get("sop_id") or sop_id
                fingerprint = latest.get("issue_fingerprint") or fingerprint
            else:
                decision, confidence, reason = "new", 0.7, "核心故障意图差异较大"
        return {
            "decision": decision, "confidence": confidence, "reason": reason,
            "fingerprint": fingerprint, "sop_id": sop_id, "features": features,
            "needs_confirmation": decision == "ambiguous",
        }

    def _extract_issue_features(self, question: str, answer: str = "") -> dict:
        text = f"{question}\n{answer[:400]}"
        code_match = re.search(r"(?:报警|告警|故障码|故障代码|代码)\s*[:：#]?\s*([A-Za-z]?\d{2,6})", text, re.IGNORECASE)
        if not code_match and re.search(r"报警|告警|故障", question):
            code_match = re.search(r"\b([A-Za-z]?\d{2,6})\b", question, re.IGNORECASE)
        device_match = re.search(r"(Fanuc|FANUC|西门子|SINUMERIK|三菱|M700|808D|0i[-\w]*|数控机床|逆变器|伺服驱动器)", text, re.IGNORECASE)
        components = ["编码器", "电池", "主轴", "伺服", "逆变器", "刀库", "电源", "传感器", "润滑", "冷却", "驱动器"]
        component = next((c for c in components if c in text), "")
        intents = []
        for word in ["过温", "过热", "更换", "复位", "参数", "验证", "报警", "异响", "欠压", "过载", "断线"]:
            if word in text:
                intents.append(word)
        return {
            "fault_code": code_match.group(1).upper() if code_match else "",
            "device_model": device_match.group(1) if device_match else "",
            "component": component,
            "intent": " ".join(dict.fromkeys(intents)),
            "tokens": sorted(self._issue_tokens(text))[:80],
        }

    def _issue_fingerprint(self, features: dict) -> str:
        parts = [
            features.get("device_model", ""), features.get("fault_code", ""),
            features.get("component", ""), features.get("intent", ""),
        ]
        if not any(parts):
            parts = features.get("tokens", [])[:12]
        return "|".join(str(p).strip().lower() for p in parts if p)

    def _issue_tokens(self, text: str) -> set[str]:
        words = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
        stop = {"步骤", "检查", "确认", "操作", "处理", "进行", "完成", "原因", "方法", "分析", "系统", "设备"}
        tokens = {w for w in words if w not in stop}
        for word in words:
            if re.fullmatch(r"[\u4e00-\u9fff]{3,}", word):
                tokens.update(word[i:i + 2] for i in range(len(word) - 1))
        return tokens

    def _similarity(self, prev: dict, current: dict) -> float:
        score = 0.0
        weight = 0.0
        for key, w in [("fault_code", 0.42), ("device_model", 0.18), ("component", 0.2), ("intent", 0.1)]:
            weight += w
            if prev.get(key) and current.get(key) and prev.get(key) == current.get(key):
                score += w
            elif prev.get(key) and not current.get(key):
                score += w * 0.45
        a, b = set(prev.get("tokens", [])), set(current.get("tokens", []))
        token_sim = len(a & b) / max(len(a | b), 1) if a or b else 0
        score += token_sim * 0.1
        weight += 0.1
        return score / max(weight, 1e-6)

    def _fingerprint_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", "", re.sub(r"^(步骤\s*)?\d+[\.\、\）\)]?", "", text.lower()))
        return hashlib.sha1(normalized[:240].encode("utf-8")).hexdigest()


sop_service = SopService()
