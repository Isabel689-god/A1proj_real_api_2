"""CNC 故障诊断 Agent — LangGraph ReAct Agent。"""
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

CNC_SYSTEM_PROMPT = """你是数控机床故障诊断专家Agent。

工作流程：先 search_knowledge_base 搜知识库，再 search_mysql_graph 查图谱，最后查用户历史，综合回答。

回答格式：具体操作问题直接答，初次诊断用完整格式（一故障诊断、二原因分析、三解决方案、四总结）。

每次回答末尾必须附加【标准作业指引】和【推荐下一步】。不论什么类型的问题都不能省略。

【标准作业指引】输出格式（严格遵循，禁止使用表格）：
步骤：
1. 动词开头，描述操作对象+检测方法+正常范围
2. 动词开头，描述操作对象+检测方法+正常范围
（至少输出4步，根据故障复杂度可扩展到8步）
规范：
- 量化要求1（含数值或公差）
- 量化要求2
注意：
- 安全事项1
- 安全事项2

【推荐下一步】3个选项，≤25字。直接用中文回答。"""

def create_cnc_agent(user_id: str = "") -> Any:
    s = get_settings()
    model = ChatOpenAI(model=s.LLM_MODEL, openai_api_key=s.api_key,
                       openai_api_base=s.api_base, temperature=0.2, max_tokens=2048, timeout=120)
    tools = [search_knowledge_base, search_mysql_graph]
    if user_id:
        @tool
        def get_user_history(query: str = "") -> str:
            """查询用户历史维修记录。"""
            return memory_service.get_memory_text(user_id) or "暂无历史。"
        tools.append(get_user_history)
    return create_react_agent(model=model, tools=tools, prompt=CNC_SYSTEM_PROMPT)
