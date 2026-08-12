"""自动同步维修记录到案例库。

当维修员提交新记录时，LLM 自动提取故障代码，检查案例库是否已有同代码案例。
新故障 → 自动同步；已有故障 → 跳过。
"""
from __future__ import annotations

import logging
import re

from app.db import get_session, MaintenanceRecord
from app.core.llm_provider import get_llm
from app.knowledge.dynamic_store import DynamicKnowledgeStore

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """从以下维修记录中提取故障代码（报警码/故障码），严格按格式输出：

{context}

输出格式（只输出一行）：
故障代码: <代码>

规则：
- 故障代码是数字/字母组合的报警码，如 176、HM31、E001、AL-12
- 如果描述中没有明确的报警码，从故障类型中推断一个短标识（如"主轴异响"→"主轴异响"）
- 不要输出多余文字，只输出"故障代码: XXX"
"""


def _extract_fault_code_llm(record: MaintenanceRecord) -> str:
    """用 LLM 从记录中提取故障代码。"""
    context = "\n".join([
        f"故障类型: {record.fault_type or '未知'}",
        f"故障描述: {record.description or '无'}",
        f"故障原因: {record.fault_cause or '无'}",
        f"维修方案: {record.solution or '无'}",
    ])
    try:
        llm = get_llm(temperature=0.1, max_tokens=32)
        resp = llm.invoke(_EXTRACT_PROMPT.format(context=context))
        text = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r"故障代码[：:]\s*(.+)", text.strip())
        if m:
            code = m.group(1).strip()[:30]
            logger.info(f"LLM 提取故障代码: {code}")
            return code
    except Exception as e:
        logger.warning(f"LLM 提取故障代码失败: {e}")

    # 回退：正则提取
    combined = f"{record.fault_type or ''} {record.description or ''}"
    m = re.search(r"\b([A-Za-z]{0,3}\d{2,6})\b", combined)
    if m:
        return m.group(1).upper()
    return (record.fault_type or "").strip()[:30] or "unknown"


def _fault_code_exists(fault_code: str) -> bool:
    """检查案例库中是否已有该故障代码的记录。"""
    db = get_session()
    try:
        exists = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.fault_type.contains(fault_code),
            MaintenanceRecord.synced == "已同步",
        ).first()
        return exists is not None
    finally:
        db.close()


def auto_sync_to_case_library(record: MaintenanceRecord) -> None:
    """自动同步一条维修记录到案例库（新故障才入库）。"""
    if not record.description and not record.fault_type:
        logger.info("空记录，跳过自动同步")
        return

    # 1. 提取故障代码
    fault_code = _extract_fault_code_llm(record)
    if not fault_code or fault_code == "unknown":
        logger.info("无法提取故障代码，跳过自动同步")
        return

    # 2. 查重
    if _fault_code_exists(fault_code):
        logger.info(f"故障代码 '{fault_code}' 已存在案例库，跳过")
        return

    # 3. 新故障 → 标记已同步
    record_id = record.record_id
    db = get_session()
    try:
        rec = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id).first()
        if rec:
            rec.synced = "已同步"
            db.commit()
            logger.info(f"记录 {record_id} 已标记为已同步")
    except Exception as e:
        logger.warning(f"更新 synced 失败: {e}")
    finally:
        db.close()

    # 4. 写入动态知识库
    try:
        store = DynamicKnowledgeStore()
        store.add_case(
            title=f"{record.device_model or '未知设备'} | {record.fault_type or fault_code}",
            content=(
                f"设备型号：{record.device_model or '未知'}\n"
                f"故障类型：{record.fault_type or '未知'}\n"
                f"故障代码：{fault_code}\n"
                f"故障原因：{record.fault_cause or '未记录'}\n"
                f"故障描述：{record.description or '未记录'}\n"
                f"维修方案：{record.solution or '未记录'}\n"
                f"维修人员：{record.technician or '未记录'}\n"
                f"是否解决：{record.fault_resolved or '是'}"
            ),
            device_model=record.device_model or "",
            tags=[record.fault_type or fault_code, fault_code],
            author="auto-sync",
        )
        # 自动审核通过
        cases = store.list_cases(status="pending")
        for case in cases:
            if case.get("title") == f"{record.device_model or '未知设备'} | {record.fault_type or fault_code}":
                store.review_case(case["id"], approve=True, reviewer="auto-sync")
                break
        logger.info(f"新故障 '{fault_code}' 已自动同步到案例库")
    except Exception as e:
        logger.warning(f"写入动态知识库失败: {e}")
