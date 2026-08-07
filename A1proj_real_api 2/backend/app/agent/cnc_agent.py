"""CNC 故障诊断 Agent — LangGraph ReAct Agent + SOP 状态管理工具。"""
from __future__ import annotations
from typing import Any
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from app.core.config import get_settings
from app.services.memory_service import memory_service
from app.langchain.rag_chain import RAGChain

@tool
def search_knowledge_base(query: str) -> str:
    """搜索知识库。新故障诊断优先使用。"""
    try:
        rag = RAGChain()
        c = rag.retrieve(query).context
        return c[:3000] if c and len(c) >= 20 else "未找到相关内容。"
    except Exception as e:
        return f"检索失败: {e}"

@tool
def search_mysql_graph(query: str) -> str:
    """查询 MySQL 知识图谱，返回故障→原因→方案。"""
    from app.db import get_session
    from sqlalchemy import text
    s = get_session()
    try:
        rows = s.execute(text("SELECT biz_id,name,description FROM fault WHERE name LIKE :q OR description LIKE :q LIMIT 5"),{"q":f"%{query}%"}).fetchall()
        lines = []
        for r in rows:
            fid=r[0]; lines.append(f"故障:{r[1]}")
            if r[2]: lines.append(f"  描述:{r[2][:100]}")
            for c in s.execute(text("SELECT dst_id FROM relation WHERE src_id=:bid AND rel_type='causes' LIMIT 3"),{"bid":fid}).fetchall():
                ci=s.execute(text("SELECT name FROM fault_cause WHERE biz_id=:bid"),{"bid":c[0]}).fetchone()
                if ci: lines.append(f"  →原因:{ci[0]}")
            for sl in s.execute(text("SELECT dst_id FROM relation WHERE src_id=:bid AND rel_type='solved_by' LIMIT 3"),{"bid":fid}).fetchall():
                si=s.execute(text("SELECT name FROM solution WHERE biz_id=:bid"),{"bid":sl[0]}).fetchone()
                if si: lines.append(f"  →方案:{si[0]}")
        return "\n".join(lines) if lines else f"未找到「{query}」。"
    finally:
        s.close()


# ═══════════ SOP 状态管理工具 ═══════════

import contextvars
_sop_session: contextvars.ContextVar = contextvars.ContextVar('sop_session', default='')


class sop_session_context:
    """上下文管理器：绑定 SOP 工具到指定会话，退出时自动解绑。"""
    def __init__(self, session_id: str):
        self.token = _sop_session.set(session_id) if session_id else None
    def __enter__(self): return self
    def __exit__(self, *args):
        if self.token is not None:
            _sop_session.reset(self.token)

@tool
def sop_manage(action: str, step_index: int = 0, status: str = "", note: str = "") -> str:
    """管理当前会话的 SOP 步骤状态。

参数说明：
- action: "create"(生成新SOP后调用一次,绑定session) | "update"(更新步骤状态) | "query"(查询当前所有步骤状态)
- step_index: 步骤编号,从1开始。update时必填。
- status: "done"(已完成) | "in_progress"(进行中) | "pending"(未开始)。update时必填。
- note: 该步骤的操作备注,可选。

用法示例：
1. create → sop_manage(action="create")
2. 步骤1完成 → sop_manage(action="update", step_index=1, status="done", note="接线牢固")
3. 开始步骤2 → sop_manage(action="update", step_index=2, status="in_progress")
4. 每次对话开头先查状态 → sop_manage(action="query")

返回：当前整个 SOP 的状态快照(JSON),含每步的 status 和 all_done 标志。"""
    from app.services.sop_service import sop_service
    import json

    session_id = _sop_session.get()
    if not session_id:
        return json.dumps({"error": "SOP 工具未绑定会话，请先创建 SOP"}, ensure_ascii=False)

    if action == "query":
        return json.dumps(sop_service.get_sop_state(session_id), ensure_ascii=False, indent=2)

    if action == "create":
        return json.dumps({"ok": True, "msg": "SOP 工具已绑定当前会话，生成 SOP 后可用 update 跟踪步骤状态"}, ensure_ascii=False)

    if action == "update":
        if not status or not step_index:
            return json.dumps({"error": "update 需要 step_index 和 status"}, ensure_ascii=False)
        result = sop_service.update_step_status(session_id, step_index, status, note)
        if result is None:
            # 检查具体失败原因
            state = sop_service.get_sop_state(session_id)
            if not state.get("exists"):
                return json.dumps({"error": "当前会话尚无SOP，请先完成首轮诊断生成SOP"}, ensure_ascii=False)
            else:
                return json.dumps({"error": f"步骤索引 {step_index} 超出范围 (共{len(state.get('steps',[]))}步), 请检查步骤编号"}, ensure_ascii=False)
        state = sop_service.get_sop_state(session_id)
        return json.dumps(state, ensure_ascii=False, indent=2)

    if action == "complete_all":
        """用户确认全部步骤完成 → 一次性标记所有步骤为 done"""
        state = sop_service.get_sop_state(session_id)
        if not state.get("exists"):
            return json.dumps({"error": "当前会话无 SOP"}, ensure_ascii=False)
        for i, s in enumerate(state["steps"], 1):
            if s["status"] != "done":
                sop_service.update_step_status(session_id, i, "done")
        state = sop_service.get_sop_state(session_id)
        return json.dumps(state, ensure_ascii=False, indent=2)

    return json.dumps({"error": f"未知 action: {action}，可选: create/update/query"}, ensure_ascii=False)


CNC_SYSTEM_PROMPT = """你是数控机床故障诊断专家Agent。

## 职责分离（核心原则）
1. **聊天界面** — 所有用户交互、故障描述、问题确认、异常沟通均在此完成。
2. **SOP（标准作业指引）** — 仅作为参考工具，输出固定维修步骤，不承载任何交互功能与状态判断。不要在 SOP 中嵌入"请回复完成""是否正常"等交互式提问。
3. **Agent（你）** — 唯一的状态管理者。通过对话上下文理解用户反馈，自行判断每步的执行情况（正常/异常/跳过/已更换），调用 sop_manage 工具更新状态，决定后续处理逻辑。

## 工具
- search_knowledge_base: 搜索知识库
- search_mysql_graph: 查询知识图谱(故障→原因→方案)
- get_user_history: 查询用户历史记录
- sop_manage: 维护 SOP 步骤状态（create/update/query/complete_all）

## SOP 状态管理（最高优先级！必须在知识库搜索之前完成）
每轮对话严格按以下顺序操作，不得跳过：
1. 首先调 sop_manage(action="query") 获取当前步骤状态。
   - 如果返回 exists=false（尚无 SOP），说明这是首轮诊断，正常生成诊断报告和 SOP 文本，不调用 update。
   - 如果返回 exists=true，继续以下步骤。
2. 根据用户消息立即更新状态：
   - 用户说"前N步完成" → 逐个调 sop_manage(action="update", step_index=1..N, status="done")
   - 用户说"第X步进行中" → 调 sop_manage(action="update", step_index=X, status="in_progress")
   - 用户说"全部完成/维修成功" → 调 sop_manage(action="complete_all")
   - 任何步骤状态变化都要调 update，不能只说不做
3. 更新完状态后，再进行知识库搜索和回答生成。
4. 如某步不适用（如"无需更换"），标记为 done 并备注"跳过"。

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
【标准作业指引】— 纯参考步骤（4-8步，动词开头+检测方法+正常范围，禁止交互式提问）
格式：
步骤：
1. xxx
2. xxx
（禁止表格）

【推荐下一步】— 3个选项，≤25字。"""


def create_cnc_agent(user_id: str = "", session_id: str = "") -> Any:
    _sop_session.set(session_id)

    s = get_settings()
    model = ChatOpenAI(model=s.LLM_MODEL, openai_api_key=s.api_key,
                       openai_api_base=s.api_base, temperature=0.2, max_tokens=3072,
                       timeout=180, max_retries=3)
    tools = [search_knowledge_base, search_mysql_graph, sop_manage]
    if user_id:
        @tool
        def get_user_history(query: str = "") -> str:
            """查询用户历史维修记录。"""
            return memory_service.get_memory_text(user_id) or "暂无历史。"
        tools.append(get_user_history)
    return create_react_agent(model=model, tools=tools, prompt=CNC_SYSTEM_PROMPT)
