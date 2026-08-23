"""自动同步维修记录到案例库。

当维修员提交新记录时，LLM 结构化提取故障信息（报警码/部件/归一化类型），
据此构建判重键检查案例库是否已有同故障案例：
- 有报警码 → 报警码精确判重，明确判定（新故障→同步 / 已有→跳过）
- 无报警码 → 组合特征(设备+部件+类型) + 语义相似度判重，
  相似度高→跳过，相似度处于中间区间→标记"待确认"交人工审核，相似度低→同步
"""
from __future__ import annotations

import logging
import re

from app.db import get_session, MaintenanceRecord
from app.core.llm_provider import get_llm
from app.knowledge.dynamic_store import DynamicKnowledgeStore

logger = logging.getLogger(__name__)

# 常见数控部件词表（与案例检索保持一致）
COMPONENTS = [
    "编码器", "电池", "主轴", "伺服", "逆变器", "刀库",
    "电源", "传感器", "润滑", "冷却", "驱动器", "变频器", "电机", "丝杠",
]

# 相似度分档阈值
SIM_DUPLICATE = 0.70   # >= 判定为已存在
SIM_PENDING = 0.40     # [0.40, 0.70) 待人工确认；< 0.40 新故障

_EXTRACT_PROMPT = """从以下维修记录中提取故障信息，严格按三行格式输出：

{context}

输出格式（只输出三行，不要多余文字）：
故障代码: <报警码/故障码；若描述中无明确报警码，填"无">
部件: <故障部件，如主轴/伺服/编码器/刀库等；无法判断填"未知">
故障类型: <归一化故障类型，去除设备型号和修饰词，如"主轴异响">

规则：
- 报警码是数字/字母组合，如 176、HM31、E001、AL-12
- 部件从常见数控部件中选：编码器、电池、主轴、伺服、逆变器、刀库、电源、传感器、润滑、冷却、驱动器、电机、丝杠
- 故障类型只保留核心故障描述，不要带设备型号
"""


def _extract_fault_info_llm(record: MaintenanceRecord) -> dict:
    """LLM 结构化提取故障信息。返回 {fault_code, component, normalized_type, has_code}。"""
    context = "\n".join([
        f"故障类型: {record.fault_type or '未知'}",
        f"故障描述: {record.description or '无'}",
        f"故障原因: {record.fault_cause or '无'}",
        f"维修方案: {record.solution or '无'}",
    ])
    info = {"fault_code": "", "component": "", "normalized_type": ""}

    try:
        llm = get_llm(temperature=0.1, max_tokens=64)
        resp = llm.invoke(_EXTRACT_PROMPT.format(context=context))
        text = resp.content if hasattr(resp, "content") else str(resp)
        m_code = re.search(r"故障代码[：:]\s*(.+)", text)
        m_comp = re.search(r"部件[：:]\s*(.+)", text)
        m_type = re.search(r"故障类型[：:]\s*(.+)", text)
        if m_code:
            code = m_code.group(1).strip().strip("。，,;；")
            if code and code not in ("无", "未知", "None", "null", "-"):
                info["fault_code"] = code[:30]
        if m_comp:
            comp = m_comp.group(1).strip().strip("。，,;；")
            if comp and comp not in ("未知", "None", "null", "-"):
                info["component"] = comp[:20]
        if m_type:
            t = m_type.group(1).strip().strip("。，,;；")
            if t and t not in ("无", "未知", "None", "null", "-"):
                info["normalized_type"] = t[:40]
    except Exception as e:
        logger.warning(f"LLM 提取故障信息失败: {e}")

    # 回退：规则/正则提取
    combined = f"{record.fault_type or ''} {record.description or ''}"
    if not info["fault_code"]:
        m = re.search(r"\b([A-Za-z]{0,3}\d{2,6})\b", combined)
        if m:
            info["fault_code"] = m.group(1).upper()
    if not info["component"]:
        for c in COMPONENTS:
            if c in combined:
                info["component"] = c
                break
    if not info["normalized_type"]:
        info["normalized_type"] = (record.fault_type or "").strip()[:40]

    return info


def _extract_fault_info_static(record: MaintenanceRecord) -> dict:
    """静态规则提取已同步记录的故障信息（不调 LLM，用于查重比对）。"""
    combined = f"{record.fault_type or ''} {record.description or ''}"
    code = ""
    m = re.search(r"\b([A-Za-z]{0,3}\d{2,6})\b", combined)
    if m:
        code = m.group(1).upper()
    component = ""
    for c in COMPONENTS:
        if c in combined:
            component = c
            break
    return {
        "fault_code": code,
        "component": component,
        "normalized_type": (record.fault_type or "").strip()[:40],
        "device_model": (record.device_model or "").strip(),
    }


def _tokenize(text: str) -> set[str]:
    words = set(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", (text or "").lower()))
    stop = {"步骤", "检查", "确认", "操作", "处理", "进行", "完成", "原因", "方法", "分析", "系统", "设备", "故障"}
    result = {w for w in words if w not in stop}
    # 中文 2-gram 展开：捕捉"主轴异响"与"主轴异响轴承磨损"的部分重叠
    for w in words:
        if re.fullmatch(r"[\u4e00-\u9fff]{3,}", w):
            result.update(w[i:i + 2] for i in range(len(w) - 1))
    return result


def _device_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    ca = a.lower().replace("-", "").replace(" ", "")
    cb = b.lower().replace("-", "").replace(" ", "")
    return ca in cb or cb in ca or any(p in cb for p in ca.split("/") if len(p) >= 3)


def _composite_similarity(info: dict, r_info: dict) -> float:
    """组合特征相似度：设备 0.2 + 部件 0.2 + 故障类型 token Jaccard 0.6（类型为核心判重维度）。"""
    score, weight = 0.0, 0.0
    if info.get("device_model") and r_info.get("device_model"):
        weight += 0.2
        if _device_match(info["device_model"], r_info["device_model"]):
            score += 0.2
    if info.get("component") and r_info.get("component"):
        weight += 0.2
        if info["component"] == r_info["component"]:
            score += 0.2
    a = _tokenize(info.get("normalized_type", ""))
    b = _tokenize(r_info.get("normalized_type", ""))
    if a or b:
        weight += 0.6
        score += 0.6 * (len(a & b) / max(len(a | b), 1))
    return score / max(weight, 1e-6)


def _dedup(record: MaintenanceRecord, info: dict) -> tuple[str, float]:
    """判重。返回 (结果, 最高相似度)，结果 ∈ {"exists", "pending", "new"}。"""
    db = get_session()
    try:
        candidates = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.synced.in_(["已同步", "待确认"]),
            MaintenanceRecord.record_id != record.record_id,
        ).all()
    finally:
        db.close()

    if not candidates:
        return "new", 0.0

    # 有报警码：报警码精确判重
    if info.get("fault_code"):
        code = info["fault_code"].upper()
        for r in candidates:
            if code and code in (r.fault_type or "").upper():
                return "exists", 1.0
        return "new", 0.0

    # 无报警码：组合特征 + 语义相似度
    cur = {**info, "device_model": record.device_model or ""}
    best = 0.0
    for r in candidates:
        r_info = _extract_fault_info_static(r)
        sim = _composite_similarity(cur, r_info)
        best = max(best, sim)
    if best >= SIM_DUPLICATE:
        return "exists", best
    if best >= SIM_PENDING:
        return "pending", best
    return "new", best


def _mark_synced(record_id: str, synced: str) -> None:
    db = get_session()
    try:
        rec = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id).first()
        if rec:
            rec.synced = synced
            db.commit()
    except Exception as e:
        logger.warning(f"更新 synced 失败: {e}")
    finally:
        db.close()


def _write_case(record: MaintenanceRecord, info: dict, author: str = "auto-sync") -> None:
    """写入动态知识库并自动审核通过。"""
    fault_code = info.get("fault_code", "")
    title = f"{record.device_model or '未知设备'} | {record.fault_type or info.get('normalized_type') or '未知故障'}"
    tags = [t for t in [record.fault_type, info.get("normalized_type"), fault_code] if t]
    store = DynamicKnowledgeStore()
    store.add_case(
        title=title,
        content=(
            f"设备型号：{record.device_model or '未知'}\n"
            f"故障类型：{record.fault_type or info.get('normalized_type') or '未知'}\n"
            f"故障代码：{fault_code or '无'}\n"
            f"故障部件：{info.get('component') or '未知'}\n"
            f"故障原因：{record.fault_cause or '未记录'}\n"
            f"故障描述：{record.description or '未记录'}\n"
            f"维修方案：{record.solution or '未记录'}\n"
            f"维修人员：{record.technician or '未记录'}\n"
            f"是否解决：{record.fault_resolved or '是'}"
        ),
        device_model=record.device_model or "",
        tags=tags,
        author=author,
    )
    cases = store.list_cases(status="pending")
    for case in cases:
        if case.get("title") == title:
            store.review_case(case["id"], approve=True, reviewer=author)
            break


def auto_sync_to_case_library(record: MaintenanceRecord) -> str:
    """自动同步一条维修记录到案例库（判重后决定：同步/跳过/待确认）。返回结果。"""
    if not record.description and not record.fault_type:
        logger.info("空记录，跳过自动同步")
        return "skip_empty"

    info = _extract_fault_info_llm(record)
    if not info.get("fault_code") and not info.get("normalized_type"):
        logger.info("无法提取任何故障信息，跳过自动同步")
        return "skip_empty"

    result, sim = _dedup(record, info)

    if result == "exists":
        logger.info(
            f"故障已存在案例库(fault_code={info.get('fault_code') or info.get('normalized_type')}, sim={sim:.2f})，跳过"
        )
        return "exists"

    if result == "pending":
        _mark_synced(record.record_id, "待确认")
        logger.info(f"无报警码且相似度处于中间区间(sim={sim:.2f})，标记待确认，交人工审核")
        return "pending"

    # 新故障 → 标记已同步 + 写入动态知识库
    _mark_synced(record.record_id, "已同步")
    try:
        _write_case(record, info)
        logger.info(f"新故障 '{info.get('fault_code') or info.get('normalized_type')}' 已自动同步到案例库")
    except Exception as e:
        logger.warning(f"写入动态知识库失败: {e}")
    return "synced"


def review_pending_record(record_id: str, approve: bool, reviewer: str = "admin") -> dict:
    """人工审核"待确认"记录。approve=True → 已同步并入库；False → 驳回为未同步。"""
    db = get_session()
    try:
        rec = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id).first()
        if not rec:
            return {"success": False, "message": "记录不存在"}
    finally:
        db.close()

    if approve:
        info = _extract_fault_info_static(rec)
        _mark_synced(record_id, "已同步")
        try:
            _write_case(rec, info, author=f"admin:{reviewer}")
        except Exception as e:
            logger.warning(f"审核通过写入案例库失败: {e}")
        return {"success": True, "synced": "已同步"}
    _mark_synced(record_id, "未同步")
    return {"success": True, "synced": "未同步"}
