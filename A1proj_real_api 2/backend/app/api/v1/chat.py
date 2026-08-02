"""聊天 API：异步端点，流式 LLM → SSE 逐句输出。"""
from __future__ import annotations

import asyncio, json, logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.chat_history import InMemoryChatMessageHistory

from app.langchain.rag_chain import RAGChain
from app.services.memory_service import memory_service
from app.services.session_service import session_service
from app.services.sop_service import sop_service
from app.agent.cnc_agent import create_cnc_agent
from app.schemas.chat import ChatStreamRequest

router = APIRouter(prefix="/chat", tags=["智能对话"])
logger = logging.getLogger(__name__)

_sessions: dict[str, InMemoryChatMessageHistory] = {}
_last_response: dict[str, Any] | None = None
_rag: RAGChain = RAGChain()


def get_last_response(session_id: str) -> dict[str, Any] | None:
    return _last_response

def reload() -> None:
    global _last_response, _rag
    _last_response = None
    _rag = RAGChain()

def _get_session(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = InMemoryChatMessageHistory()
    return _sessions[session_id]


def _split_chunks(text: str) -> list[str]:
    """按句子边界切分，每段不超过 30 字，保证前端流式渲染。"""
    import re
    chunks = re.split(r'(?<=[。！？\n])', text)
    result = []
    for c in chunks:
        if not c:
            continue
        while len(c) > 30:
            result.append(c[:30])
            c = c[30:]
        if c:
            result.append(c)
    return result if result else [text]


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest):
    """SSE 端点：流式 LLM → 逐句推送到前端。"""
    try:
        logger.info(f"流式对话 | user={req.user_id}, session={req.session_id}")
        global _last_response

        loop = asyncio.get_event_loop()
        retrieval = await loop.run_in_executor(
            None, _rag.retrieve, req.question, req.device_model, req.image_url, req.user_id
        )

        async def sse_generator():
            full_answer = ""
            buffer = ""
            try:
                async for chunk in _rag.astream(retrieval):
                    full_answer += chunk
                    buffer += chunk
                    if any(sep in buffer for sep in ("。", "！", "？", "\n")):
                        for piece in _split_chunks(buffer):
                            yield f"data: {json.dumps({'type': 'text', 'content': piece}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.03)
                        buffer = ""
                if buffer:
                    for piece in _split_chunks(buffer):
                        yield f"data: {json.dumps({'type': 'text', 'content': piece}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.warning(f"流式生成异常，降级为非流式: {e}")
                full_answer = await loop.run_in_executor(None, _rag.generate, retrieval)

            if not full_answer or len(full_answer.strip()) < 5:
                full_answer = (
                    "⚠️ 大模型服务暂时繁忙（API 限速），请稍后重试。"
                    "以下为知识库中匹配到的相关内容，可供参考：\n\n"
                )
                for i, doc in enumerate(retrieval.final_docs[:3], 1):
                    content = doc.get("content", "")[:200]
                    if content:
                        full_answer += f"📄 {doc.get('title', '资料'+str(i))}：{content}\n\n"
                yield f"data: {json.dumps({'type': 'text', 'content': full_answer}, ensure_ascii=False)}\n\n"

            docs = retrieval.final_docs
            sources = [
                {"title": d.get("title"), "source": d.get("source"), "score": d.get("score")}
                for d in docs
            ]
            confidence = round(max([d.get("score", 0) for d in docs] + [0]), 4)
            _last_response = {
                "answer": full_answer, "sources": sources, "confidence": confidence,
                "provider": f"langchain:{_rag.settings.LLM_MODEL}",
            }
            _get_session(req.session_id).add_user_message(req.question)
            _get_session(req.session_id).add_ai_message(full_answer)

            # 持久化会话到 JSON 文件
            try:
                hist = _get_session(req.session_id)
                msgs = [
                    {"role": "user" if m.type == "human" else "assistant", "content": m.content}
                    for m in hist.messages
                ]
                title = req.question[:20] if len(msgs) <= 4 else ""
                session_service.save(req.session_id, req.user_id, msgs, title)
            except Exception:
                pass

            # 自动更新用户长期记忆
            if req.user_id:
                try:
                    memory_service.update_from_conversation(
                        req.user_id, req.question, full_answer, req.device_model
                    )
                except Exception:
                    pass  # 记忆更新失败不影响主流程

            if sources:
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
            sop_steps = _parse_sop_steps(full_answer)
            if sop_steps:
                sop_record = sop_service.save_version(
                    req.session_id,
                    req.user_id,
                    req.question,
                    sop_steps[:8],
                    full_answer,
                )
                yield f"data: {json.dumps({'type': 'sop_version', 'sop': sop_record}, ensure_ascii=False)}\n\n"
            yield 'data: {"type": "done"}\n\n'

        return StreamingResponse(sse_generator(), media_type="text/event-stream")
    except Exception as exc:
        logger.error(f"对话异常: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stream/multipart")
async def chat_stream_multipart(
    user_id: str = Form(...), session_id: str = Form(...),
    question: str = Form(...), device_model: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    import base64
    image_url = None
    if image and image.filename:
        data = await image.read()
        mime = image.content_type or "image/jpeg"
        image_url = f"data:{mime};base64,{base64.standard_b64encode(data).decode('ascii')}"
    req = ChatStreamRequest(
        user_id=user_id, session_id=session_id,
        question=question, device_model=device_model, image_url=image_url,
    )
    return await chat_stream(req)


# ═══════════ Agent 多步推理端点 ═══════════


def _tool_label(name: str) -> str:
    """工具名 → 中文标签。"""
    return {
        "search_knowledge_base": "搜索知识库",
        "search_mysql_graph": "查询图谱",
        "get_user_history": "查询记忆",
    }.get(name, name)


def _parse_suggestions(text: str) -> list[str]:
    """从文本中解析【推荐下一步】为选项列表。"""
    import re as _r
    match = _r.search(r'【推荐下一步】\s*\n(.*?)(?:\n\n|\Z)', text, _r.DOTALL)
    if not match:
        # 也匹配 ## 【推荐下一步】 格式
        match = _r.search(r'#{1,2}\s*【推荐下一步】\s*\n(.*?)(?:\n\n|\Z)', text, _r.DOTALL)
    if not match:
        return []
    items = []
    for line in match.group(1).strip().split('\n'):
        m = _r.match(r'\d+\.\s*(.+)', line.strip())
        if m:
            t = m.group(1).strip().rstrip('。！？.')
            if t and len(t) <= 40:
                items.append(t)
    return items[:3]


def _parse_sop_steps(text: str) -> list[dict]:
    """从文本中解析SOP步骤，多级回退保证不空。"""
    import re as _r
    steps = []

    # 1. 尝试【标准作业指引】板块（兼容 markdown 标题）
    match = _r.search(r'#{0,2}\s*【标准作业指引】([\s\S]*?)(?=#{0,2}\s*【推荐下一步】|\Z)', text)
    if match:
        block = match.group(1)
        # 1a. 冒号格式：步骤：\n1. xxx\n2. yyy
        sec = _r.search(r'步骤[：:]\s*\n(.*?)(?=规范[：:]|注意[：:]|\Z)', block, _r.DOTALL)
        if sec:
            for line in sec.group(1).split('\n'):
                m = _r.match(r'(\d+)[\.\、\）\)]\s*(.+)', line.strip())
                if m: steps.append({'title': f'步骤 {m.group(1)}', 'desc': m.group(2).strip()[:120]})
        # 1b. 表格格式：| 步骤 | 操作对象 | ... → 按列提取
        if not steps:
            step_col_idx = -1
            for line in block.split('\n'):
                line = line.strip()
                if not line.startswith('|') or line.startswith('|-'):
                    continue
                cells = [c.strip() for c in line.strip('|').split('|')]
                # 表头行：找到「步骤」列
                if step_col_idx < 0:
                    for i, c in enumerate(cells):
                        if '步骤' in c:
                            step_col_idx = i
                            break
                    continue
                # 数据行
                if step_col_idx >= 0 and step_col_idx < len(cells):
                    num_match = _r.match(r'(\d+)[\.\、\）\)]?\s*(.*)', cells[step_col_idx])
                    if num_match:
                        rest = ' | '.join(cells[step_col_idx+1:]).strip() if step_col_idx+1 < len(cells) else ''
                        desc = f"{num_match.group(2)} | {rest}" if rest else num_match.group(2)
                        steps.append({'title': f'步骤 {num_match.group(1)}', 'desc': desc[:120]})
        # 规范
        spec = _r.search(r'规范[：:]\s*\n(.*?)(?=注意[：:]|\Z)', block, _r.DOTALL)
        if spec:
            ls = [l.strip().lstrip('-·•').strip() for l in spec.group(1).split('\n') if l.strip().lstrip('-·•').strip()]
            if ls: steps.append({'title': '📐 操作规范', 'desc': '；'.join(ls[:3])[:120]})
        # 注意
        note = _r.search(r'注意[：:]\s*\n(.*?)(?:\Z)', block, _r.DOTALL)
        if note:
            ls = [l.strip().lstrip('-·•').strip() for l in note.group(1).split('\n') if l.strip().lstrip('-·•').strip()]
            if ls: steps.append({'title': '⚠️ 安全注意', 'desc': '；'.join(ls[:3])[:120]})

    # 2. 回退：从「三、解决方案」提取编号步骤
    if not steps:
        sol = _r.search(r'三[、.]\s*解决方案[\s\S]*?(?=四[、.]|【推荐|【标准|\Z)', text)
        if sol:
            for line in sol.group(0).split('\n'):
                m = _r.match(r'(\d+)[\.\、\)）]\s*(.+)', line.strip())
                if m: steps.append({'title': f'步骤 {m.group(1)}', 'desc': m.group(2).strip()[:120]})

    # 3. 回退：从全文提取任意编号列表（最多5条）
    if not steps:
        for line in text.split('\n'):
            m = _r.match(r'(\d+)[\.\、\)）]\s*(.+)', line.strip())
            if m and len(m.group(2)) > 8:
                steps.append({'title': f'步骤 {m.group(1)}', 'desc': m.group(2).strip()[:120]})
            if len(steps) >= 5: break

    # 4. 回退：提取表格行
    if not steps:
        for line in text.split('\n'):
            if '|' in line and not line.startswith('|-') and not line.startswith('| '):
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 1 and len(cells[0]) > 3:
                    steps.append({'title': cells[0][:30], 'desc': ' | '.join(cells[1:3])[:120] if len(cells) > 1 else cells[0][:120]})
            if len(steps) >= 5: break

    return steps[:8]


def _attach_latest_sop(session: dict) -> dict:
    """将当前 SOP 版本挂到最后一条助手消息，便于刷新后右侧原位恢复。"""
    latest = sop_service.get_latest(session.get("session_id", ""))
    if not latest:
        return session
    for msg in reversed(session.get("messages", [])):
        if msg.get("role") == "assistant":
            msg["current_sop"] = latest
            msg["sop_steps"] = latest.get("steps", [])
            break
    return session


@router.post("/agent")
async def chat_agent(req: ChatStreamRequest):
    """Agent 端点：LLM 自主规划 + 多工具调用，流式输出诊断报告。"""
    try:
        logger.info(f"Agent诊断 | user={req.user_id}, session={req.session_id}")

        agent = create_cnc_agent(req.user_id)

        async def sse_generator():
            full_answer = ""
            try:
                # 构建消息（含历史上下文）
                import re as _cleanre
                input_text = req.question
                if req.device_model:
                    input_text = f"设备型号：{req.device_model}\n{input_text}"
                messages = []
                hist = _get_session(req.session_id)
                sop_context = sop_service.get_iteration_context(req.session_id)
                if sop_context:
                    messages.append({
                        "role": "user",
                        "content": (
                            f"{sop_context}\n\n"
                            "如果本轮是同一故障链路的追问，请在原 SOP 基础上补充或改写对应步骤，"
                            "不要把它当成新的独立 SOP；只有设备、告警代码或根因明显变化时才重新组织。"
                        ),
                    })
                for m in hist.messages[-6:]:
                    content = m.content
                    if isinstance(content, str):
                        content = _cleanre.sub(r'【标准作业指引】[\s\S]*', '', content).strip()
                        content = _cleanre.sub(r'【推荐下一步】[\s\S]*', '', content).strip()
                    role = "assistant" if m.type == "ai" else "user"
                    messages.append({"role": role, "content": content})
                messages.append({"role": "user", "content": input_text})

                token_usage = {"prompt": 0, "completion": 0, "total": 0}

                async for event in agent.astream_events(
                    {"messages": messages},
                    version="v2",
                ):
                    kind = event.get("event", "")
                    # 工具调用事件
                    if kind == "on_tool_start":
                        name = event.get("name", "")
                        yield f"data: {json.dumps({'type': 'tool_start', 'tool': name, 'label': _tool_label(name)}, ensure_ascii=False)}\n\n"
                    elif kind == "on_tool_end":
                        name = event.get("name", "")
                        output = str(event.get("data", {}).get("output", ""))[:200]
                        yield f"data: {json.dumps({'type': 'tool_end', 'tool': name, 'label': _tool_label(name), 'output': output}, ensure_ascii=False)}\n\n"
                    # LLM 文本输出
                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk", {})
                        # 捕获 token 用量
                        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                            token_usage["prompt"] = chunk.usage_metadata.get("input_tokens", 0)
                            token_usage["completion"] = chunk.usage_metadata.get("output_tokens", 0)
                            token_usage["total"] = chunk.usage_metadata.get("total_tokens", 0)
                        if hasattr(chunk, "content") and chunk.content:
                            text = chunk.content
                            full_answer += text
                            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.warning(f"Agent异常: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

            # 从回答文本中解析建议和SOP
            import re as _re2
            suggestions = _parse_suggestions(full_answer)
            if suggestions:
                yield f"data: {json.dumps({'type': 'suggestions', 'items': suggestions[:3]}, ensure_ascii=False)}\n\n"
            sop_steps = _parse_sop_steps(full_answer)
            if sop_steps:
                sop_record = sop_service.save_version(
                    req.session_id,
                    req.user_id,
                    req.question,
                    sop_steps[:8],
                    full_answer,
                )
                yield f"data: {json.dumps({'type': 'sop_version', 'sop': sop_record}, ensure_ascii=False)}\n\n"

            # 发送 token 用量
            if token_usage["total"] > 0:
                yield f"data: {json.dumps({'type': 'token_usage', 'usage': token_usage}, ensure_ascii=False)}\n\n"

            # 持久化
            _get_session(req.session_id).add_user_message(req.question)
            _get_session(req.session_id).add_ai_message(full_answer)
            try:
                hist = _get_session(req.session_id)
                msgs = [{"role": "user" if m.type == "human" else "assistant", "content": m.content} for m in hist.messages]
                title = req.question[:20] if len(msgs) <= 4 else ""
                session_service.save(req.session_id, req.user_id, msgs, title)
            except Exception:
                pass

            # 长期记忆
            if req.user_id:
                try:
                    memory_service.update_from_conversation(
                        req.user_id, req.question, full_answer, req.device_model
                    )
                except Exception:
                    pass

            yield 'data: {"type": "done"}\n\n'

        return StreamingResponse(sse_generator(), media_type="text/event-stream")
    except Exception as exc:
        logger.error(f"Agent异常: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════ 会话管理 ═══════════

@router.get("/sessions")
def list_sessions(user_id: str):
    """列出用户的所有历史会话（仅元数据）。"""
    return {"sessions": session_service.list_by_user(user_id)}


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, user_id: str | None = None):
    """加载指定会话的完整消息。"""
    data = session_service.load(session_id, user_id=user_id)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")
    data = _attach_latest_sop(data)
    # 同时恢复内存中的会话
    from langchain_core.chat_history import InMemoryChatMessageHistory
    from langchain_core.messages import HumanMessage, AIMessage
    hist = InMemoryChatMessageHistory()
    for m in data.get("messages", []):
        if m["role"] == "user":
            hist.add_user_message(m["content"])
        elif m["role"] == "assistant":
            hist.add_ai_message(m["content"])
    _sessions[session_id] = hist
    return {"session": data}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user_id: str | None = None):
    """删除指定会话。"""
    ok = session_service.delete(session_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    _sessions.pop(session_id, None)
    return {"success": True}
