"""CNC 故障诊断 Agent -- LangGraph ReAct Agent + 案例优先检索。
检索优先级: 案例库 -> 知识库 -> 图谱 -> SOP
"""

from __future__ import annotations

import contextvars
import json
from typing import Any

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from app.core.config import get_settings
from app.services.memory_service import memory_service
from app.services.case_service import case_service


@tool
def search_case_library(query: str, device_model: str = "", fault_code: str = "") -> str:
    """优先检索维修案例库 -- 查历史维修记录。

    参数:
    - query: 故障描述或关键词
    - device_model: 设备型号(可选)，如 "FANUC 0i-MF"
    - fault_code: 报警代码(可选)，如 "1032"

    返回匹配案例列表。案例格式: 设备型号 | 故障类型 | 故障原因 | 解决方案 | 匹配度分。
    """
    try:
        result = case_service.search(
            question=query,
            device_model=device_model or None,
            fault_code=fault_code or None,
        )
        if not result.get("cases"):
            return json.dumps(
                {"found": False, "message": "案例库中无匹配记录"},
                ensure_ascii=False,
            )

        cases_summary = []
        for c in result["cases"]:
            cases_summary.append({
                "record_id": c["record_id"],
                "device": c["device_model"],
                "fault": c["fault_type"],
                "cause": c["fault_cause"],
                "solution": c["solution"][:300],
                "score": c["score"],
                "reason": c["match_reason"],
            })

        return json.dumps({
            "found": True,
            "matched": result["matched"],
            "confidence": result["confidence"],
            "cases": cases_summary,
            "hint": (
                "如果 confidence >= 0.70，可直接复用案例方案，"
                "结合维修手册中的参数规范交叉验证。"
                "如果 confidence < 0.70，应改用 search_knowledge_base 检索手册。"
            ),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"案例检索失败: {e}"}, ensure_ascii=False)


@tool
def search_knowledge_base(query: str) -> str:
    """搜索知识库(维修手册PDF/DOCX/XLSX)。案例库无匹配时使用。"""
    try:
        from app.langchain.rag_chain import RAGChain
        rag = RAGChain()
        c = rag.retrieve(query).context
        return c[:3000] if c and len(c) >= 20 else "未找到相关内容。"
    except Exception as e:
        return f"检索失败: {e}"


@tool
def search_mysql_graph(query: str) -> str:
    """查询 MySQL 知识图谱，返回故障->原因->方案关联链路。"""
    from app.db import get_session
    from sqlalchemy import text
    s = get_session()
    try:
        rows = s.execute(
            text(
                "SELECT biz_id,name,description FROM fault "
                "WHERE name LIKE :q OR description LIKE :q LIMIT 5"
            ),
            {"q": f"%{query}%"},
        ).fetchall()
        lines = []
        for r in rows:
            fid = r[0]
            lines.append(f"故障:{r[1]}")
            if r[2]:
                lines.append(f"  描述:{r[2][:100]}")
            for c in s.execute(
                text(
                    "SELECT dst_id FROM relation "
                    "WHERE src_id=:bid AND rel_type='causes' LIMIT 3"
                ),
                {"bid": fid},
            ).fetchall():
                ci = s.execute(
                    text("SELECT name FROM fault_cause WHERE biz_id=:bid"),
                    {"bid": c[0]},
                ).fetchone()
                if ci:
                    lines.append(f"  ->原因:{ci[0]}")
            for sl in s.execute(
                text(
                    "SELECT dst_id FROM relation "
                    "WHERE src_id=:bid AND rel_type='solved_by' LIMIT 3"
                ),
                {"bid": fid},
            ).fetchall():
                si = s.execute(
                    text("SELECT name FROM solution WHERE biz_id=:bid"),
                    {"bid": sl[0]},
                ).fetchone()
                if si:
                    lines.append(f"  ->方案:{si[0]}")
        return "\n".join(lines) if lines else f"未找到「{query}」。"
    finally:
        s.close()


# ---- SOP 状态管理（闭包版，不依赖 ContextVar）----

def _make_sop_manage(session_id: str):
    """创建绑定指定会话的 sop_manage 工具。闭包捕获 session_id，无 ContextVar 依赖。"""
    from app.services.sop_service import sop_service as svc

    @tool
    def sop_manage(action: str, step_index: int = 0, status: str = "", note: str = "", steps_json: str = "") -> str:
        """管理当前会话的 SOP 步骤状态。

        参数:
        - action: create|update|query|complete_all|batch_update
        - step_index: 步骤编号(1开始), update时必填
        - status: done|in_progress|pending, update时必填
        - note: 操作备注,可选
        - steps_json: batch_update时必填, JSON数组如 '[{"step":1,"status":"done"},{"step":2,"status":"done"}]'

        用法:
        1. create -> sop_manage(action="create")
        2. 多步更新(推荐) -> sop_manage(action="batch_update", steps_json='[{"step":1,"status":"done"},{"step":2,"status":"done"},{"step":3,"status":"in_progress"}]')
        3. 单步更新 -> sop_manage(action="update", step_index=1, status="done", note="接线牢固")
        4. 全部完成 -> sop_manage(action="complete_all")
        5. 查状态 -> sop_manage(action="query")

        **重要：需要更新多个步骤时优先用 batch_update，一次写入避免重复 I/O。**
        """
        if not session_id:
            return json.dumps({"error": "SOP 工具未绑定会话"}, ensure_ascii=False)

        if action == "query":
            return json.dumps(svc.get_sop_state(session_id), ensure_ascii=False, indent=2)

        if action == "create":
            return json.dumps(
                {"ok": True, "msg": "SOP 工具已绑定，生成 SOP 后可用 update 跟踪步骤状态"},
                ensure_ascii=False,
            )

        if action == "batch_update":
            if not steps_json:
                return json.dumps({"error": "batch_update 需要 steps_json 参数"}, ensure_ascii=False)
            try:
                updates_raw = json.loads(steps_json)
            except json.JSONDecodeError:
                return json.dumps({"error": "steps_json 格式错误，应为 JSON 数组"}, ensure_ascii=False)
            batch = []
            for u in updates_raw:
                si = int(u.get("step", 0))
                st = str(u.get("status", ""))
                nt = str(u.get("note", ""))
                if si < 1 or st not in ("done", "in_progress", "pending"):
                    return json.dumps({"error": f"无效条目: step={si}, status={st}"}, ensure_ascii=False)
                batch.append((si, st, nt))
            result = svc.batch_update_steps(session_id, batch)
            if result is None:
                return json.dumps({"error": "当前会话尚无SOP"}, ensure_ascii=False)
            return json.dumps(svc.get_sop_state(session_id), ensure_ascii=False, indent=2)

        if action == "update":
            if not status or not step_index:
                return json.dumps({"error": "需要 step_index 和 status"}, ensure_ascii=False)
            result = svc.update_step_status(session_id, step_index, status, note)
            if result is None:
                state = svc.get_sop_state(session_id)
                if not state.get("exists"):
                    return json.dumps({"error": "当前会话尚无SOP"}, ensure_ascii=False)
                return json.dumps(
                    {"error": f"步骤索引 {step_index} 超出范围 (共{len(state.get('steps',[]))}步)"},
                    ensure_ascii=False,
                )
            return json.dumps(svc.get_sop_state(session_id), ensure_ascii=False, indent=2)

        if action == "complete_all":
            state = svc.get_sop_state(session_id)
            if not state.get("exists"):
                return json.dumps({"error": "当前会话无 SOP"}, ensure_ascii=False)
            # 批量标记所有未完成步骤为 done，一次写入
            batch = []
            for i, s in enumerate(state["steps"], 1):
                if s["status"] != "done":
                    batch.append((i, "done", ""))
            if batch:
                svc.batch_update_steps(session_id, batch)
            return json.dumps(svc.get_sop_state(session_id), ensure_ascii=False, indent=2)

        return json.dumps({"error": f"未知 action: {action}"}, ensure_ascii=False)

    return sop_manage


CNC_SYSTEM_PROMPT = """你是数控机床故障诊断专家Agent。

## 检索优先级（严格按此顺序，不得跳过）

1. **search_case_library** — 最高优先级。先查历史维修案例库。
   - 如果 confidence >= 0.70（matched=true），直接复用案例的维修方案。
   - 结合 search_knowledge_base 查手册，交叉验证案例中的参数和安全规范。
   - 如果 confidence < 0.70，说明无现成案例，进入第2步。

2. **search_knowledge_base** — 案例库无匹配时，检索维修手册。
   - 同时用 search_mysql_graph 查知识图谱，获取故障->原因->方案的关联链路。
   - 图谱提供因果推理，手册提供具体参数和操作规范。

3. **sop_manage** — 生成 SOP 后，更新步骤状态。
   - **批量更新优先**：需要更新2个及以上步骤时，必须用 batch_update 一次完成，禁止逐个调 update。
     例：前3步完成、第4步进行中 → sop_manage(action="batch_update", steps_json='[{"step":1,"status":"done"},{"step":2,"status":"done"},{"step":3,"status":"done"},{"step":4,"status":"in_progress"}]')
   - 仅单步更新时才用 action="update"。
   - 全部步骤完成时用 action="complete_all"。
   - 首次诊断时，生成 SOP 后调 sop_manage(action="query") 确认绑定。
   - 每轮对话开头先调 sop_manage(action="query") 获取当前步骤状态。

## 职责分离

1. **聊天界面** — 所有用户交互、故障描述、问题确认在此完成。
2. **SOP** — 仅作为参考工具，输出固定维修步骤，禁止在SOP中嵌入交互式提问。
3. **Agent(你)** — 唯一的状态管理者。通过对话理解用户反馈，自行判断每步执行情况，调用sop_manage更新状态。

## 回答格式

初次诊断用完整格式：
## 一、故障诊断
现象+机型+报警码
## 二、原因分析
直接原因+根本原因+排除项
## 三、解决方案
具体排查步骤
## 四、经验总结

每轮回答末尾必须附加：
【标准作业指引】-- 仅首次诊断时输出，一旦生成步骤内容即冻结不可修改。后续追问时禁止输出此章节，禁止修改步骤描述，禁止追加新步骤，只需通过 sop_manage 更新步骤状态。
格式:
步骤:
1. xxx
2. xxx
(禁止表格)

【推荐下一步】-- 3个选项，<=25字。"""


def create_cnc_agent(user_id: str = "", session_id: str = "") -> Any:
    s = get_settings()
    model = ChatOpenAI(
        model=s.LLM_MODEL,
        openai_api_key=s.api_key,
        openai_api_base=s.api_base,
        temperature=0.2,
        max_tokens=3072,
        timeout=180,
        max_retries=3,
    )

    # 闭包创建 sop_manage，session_id 硬编码在闭包里，不依赖 ContextVar
    sop_manage = _make_sop_manage(session_id)

    tools = [search_case_library, search_knowledge_base, search_mysql_graph, sop_manage]

    if user_id:
        @tool
        def get_user_history(query: str = "") -> str:
            """查询用户历史维修记录。"""
            return memory_service.get_memory_text(user_id) or "暂无历史。"

        tools.append(get_user_history)

    return create_react_agent(model=model, tools=tools, prompt=CNC_SYSTEM_PROMPT)
