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
from app.vision.vision_service import VisionService

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
            # 已有 SOP 时跳过步骤解析，永不重建（对齐 chat_agent 端点）
            existing = sop_service.get_latest(req.session_id)
            sop_record = None
            if not (existing and existing.get("steps")):
                sop_steps = _parse_sop_steps(full_answer)
                if sop_steps:
                    try:
                        sop_record = sop_service.save_version(
                            req.session_id,
                            req.user_id,
                            req.question,
                            sop_steps[:8],
                            full_answer,
                        )
                        # 注入 Agent 通过 sop_manage 维护的步骤状态
                        state = sop_service.get_sop_state(req.session_id)
                        if state.get("exists"):
                            sop_record["current_step"] = state.get("current_step", 1)
                            sop_record["all_done"] = state.get("all_done", False)
                            for i, s in enumerate(sop_record.get("steps", [])):
                                if i < len(state.get("steps", [])):
                                    s["step_status"] = state["steps"][i].get("status", "pending")
                                    s["step_note"] = state["steps"][i].get("note", "")
                        yield f"data: {json.dumps({'type': 'sop_version', 'sop': sop_record}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.warning(f"save_version 失败: {e}")
            # 即使不重建，也要推 sop_version 给前端
            elif existing:
                sop_record = existing
                state = sop_service.get_sop_state(req.session_id)
                if state.get("exists"):
                    sop_record["current_step"] = state.get("current_step", 1)
                    sop_record["all_done"] = state.get("all_done", False)
                    for i, s in enumerate(sop_record.get("steps", [])):
                        if i < len(state.get("steps", [])):
                            s["step_status"] = state["steps"][i].get("status", "pending")
                            s["step_note"] = state["steps"][i].get("note", "")
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
    # 有图片时走 Agent 路径，显示完整工作流程
    if image_url:
        return await chat_agent(req)
    return await chat_stream(req)


# ═══════════ Agent 多步推理端点 ═══════════


def _tool_label(name: str) -> str:
    """工具名 → 中文标签。"""
    return {
        "search_knowledge_base": "搜索知识库",
        "search_mysql_graph": "查询图谱",
        "get_user_history": "查询记忆",
        "sop_manage": "SOP状态管理",
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


def _auto_apply_sop_updates(session_id: str, text: str, user_text: str = "") -> None:
    """扫描 Agent 回复及用户提问中的 SOP 状态更新意图，自动执行。"""
    import re as _r
    try:
        combined = f"{user_text}\n{text}" if user_text else text
        state = sop_service.get_sop_state(session_id)
        if not state.get("exists") or not state.get("steps"):
            return

        total = len(state["steps"])
        batch: list[tuple[int, str, str]] = []

        _CN_MAP = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,"两":2}
        def _num(s: str) -> int:
            s = s.strip()
            if s.isdigit(): return int(s)
            if s in _CN_MAP: return _CN_MAP[s]
            if s.endswith("十"):
                n = _CN_MAP.get(s[0], 0)
                return n * 10 if n > 0 else 10
            if s.startswith("十"):
                n = _CN_MAP.get(s[1], 0)
                return 10 + n if n > 0 else 10
            return 999

        _NUM = r'(\d+|[一二三四五六七八九十两]+)'

        # "全部步骤已完成" / "所有步骤已完成"
        if _r.search(r'(?:全部|所有)\s*步骤\s*(?:已|已经|均已)?\s*(?:完成|做完|done)', combined):
            for i in range(1, total + 1):
                batch.append((i, "done", "自动"))

        # "所有故障已解决" / "故障已解决" / "问题已解决"
        if _r.search(r'(?:所有|全部)\s*(?:故障|问题)\s*(?:已|已经|均已)?\s*(?:解决|修复|排除|处理完)', combined):
            for i in range(1, total + 1):
                batch.append((i, "done", "自动"))

        # "第4步之前已完成" → 前3步 done
        m = _r.search(r'第\s*' + _NUM + r'\s*步?\s*之前\s*(?:已|全部)?\s*(?:完成|做完)', combined)
        if m:
            n = _num(m.group(1)) - 1
            if n >= 1:
                for i in range(1, min(n, total) + 1):
                    batch.append((i, "done", "自动"))

        # "前3步已完成" / "前面3步已完成" → 前N步 done
        m = _r.search(r'前\s*面?\s*' + _NUM + r'\s*步?\s*(?:标记|已|全部|为)?\s*(?:完成|done)', combined)
        if m:
            n = _num(m.group(1))
            for i in range(1, min(n, total) + 1):
                batch.append((i, "done", "自动"))

        # "步骤1-4标记完成" → 范围 done
        m = _r.search(r'步骤\s*' + _NUM + r'\s*[-–—至到]\s*' + _NUM + r'\s*步?\s*(?:标记|已|全部|为)?\s*(?:完成|done)', combined)
        if m:
            start, end = _num(m.group(1)), _num(m.group(2))
            for i in range(max(1, start), min(end, total) + 1):
                batch.append((i, "done", "自动"))

        # "步骤1、2、3已完成"
        _NUM_LIST = r'((?:' + _NUM + r'\s*[、,，]\s*)+' + _NUM + r')'
        for m in _r.finditer(r'(?:步骤)\s*' + _NUM_LIST + r'\s*(?:标记为?|设置为?|已|为)?\s*(?:完成|done)', combined):
            nums = _r.findall(_NUM, m.group(1))
            for num_str in nums:
                idx = _num(num_str)
                if 1 <= idx <= total:
                    batch.append((idx, "done", "自动"))

        # "步骤X标记为完成" / "✅ 步骤1：... — 已完成"
        for m in _r.finditer(r'(?:步骤|第)\s*' + _NUM + r'.*?[-–—]\s*(?:已)?\s*(?:完成|done)', combined):
            idx = _num(m.group(1))
            if 1 <= idx <= total:
                batch.append((idx, "done", "自动"))

        # "步骤X进行中"
        for m in _r.finditer(r'(?:步骤|第)\s*' + _NUM + r'.*?[-–—]\s*(?:进行中|in.progress)', combined, _r.IGNORECASE):
            idx = _num(m.group(1))
            if 1 <= idx <= total:
                batch.append((idx, "in_progress", "自动"))
        for m in _r.finditer(r'(?:步骤|第)\s*' + _NUM + r'\s*步?\s*(?:标记为?|设置为?|为)?\s*(?:进行中|in.progress)', combined, _r.IGNORECASE):
            idx = _num(m.group(1))
            if 1 <= idx <= total:
                batch.append((idx, "in_progress", "自动"))

        if batch:
            sop_service.batch_update_steps(session_id, batch)
            logger.info(f"自动更新 SOP 状态: session={session_id}, {len(batch)}步")
    except Exception as e:
        logger.warning(f"自动 SOP 更新失败: {e}")


def _attach_latest_sop(session: dict) -> dict:
    """将首版 SOP 结构挂到最后一条助手消息。"""
    state = sop_service.get_sop_state(session.get("session_id", ""))
    if not state.get("exists"):
        return session
    sop = {
        "version": 1,
        "sop_id": state.get("sop_id", ""),
        "steps": [{
            "title": s["title"],
            "desc": s["desc"],
            "step_status": s["status"],
            "step_note": s["note"],
        } for s in state["steps"]],
        "current_step": state.get("current_step", 1),
        "all_done": state.get("all_done", False),
    }
    for msg in reversed(session.get("messages", [])):
        if msg.get("role") == "assistant":
            msg["current_sop"] = sop
            msg["sop_steps"] = sop["steps"]
            break
    return session


@router.post("/agent")
async def chat_agent(req: ChatStreamRequest):
    """Agent 端点：LLM 自主规划 + 多工具调用，流式输出诊断报告。"""
    try:
        logger.info(f"Agent诊断 | user={req.user_id}, session={req.session_id}")

        agent = create_cnc_agent(req.user_id, req.session_id)

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
                            "以上 SOP 步骤内容已冻结不可修改。本轮只需根据用户反馈更新对应步骤的状态，"
                            "不要改动步骤标题和描述，不要追加新步骤。"
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

                # 如果有图片，先用视觉模型识别为文字，再注入到消息中
                if req.image_url:
                    try:
                        vision = VisionService()
                        result = vision.analyze_image_url(req.image_url)
                        desc = result.get("description", "")
                        if desc:
                            last_msg = messages[-1]
                            text = last_msg["content"]
                            last_msg["content"] = f"[图片识别结果]\n{desc}\n\n[用户问题]\n{text}"
                    except Exception as ve:
                        logger.warning(f"视觉识别失败: {ve}")

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
                        # sop_manage 调用后立即推送 SOP 状态给前端
                        if name == "sop_manage":
                            try:
                                sop_state = sop_service.get_sop_state(req.session_id)
                                if sop_state.get("exists"):
                                    yield f"data: {json.dumps({'type': 'sop_state', 'state': sop_state}, ensure_ascii=False)}\n\n"
                            except Exception:
                                pass
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
                import traceback
                err_msg = str(e)
                logger.warning(f"Agent异常: {err_msg}\n{traceback.format_exc()}")
                if full_answer and len(full_answer) > 50:
                    pass
                elif "402" in err_msg or "Insufficient Balance" in err_msg:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'DeepSeek API 余额不足(402)，请充值后重试'}, ensure_ascii=False)}\n\n"
                elif "Expecting value" in err_msg or "line 1 column 1" in err_msg:
                    yield f"data: {json.dumps({'type': 'error', 'error': '模型返回空响应，正在重试…'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'error': '模型服务暂时不稳定，请重试'}, ensure_ascii=False)}\n\n"

            # 从回答文本中解析建议
            import re as _re2
            suggestions = _parse_suggestions(full_answer)
            if suggestions:
                yield f"data: {json.dumps({'type': 'suggestions', 'items': suggestions[:3]}, ensure_ascii=False)}\n\n"

            # 已有 SOP 时跳过步骤解析，永不重建
            existing = sop_service.get_latest(req.session_id)
            sop_record = None
            if not (existing and existing.get("steps")):
                sop_steps = _parse_sop_steps(full_answer)
                if sop_steps:
                    try:
                        sop_record = sop_service.save_version(
                            req.session_id,
                            req.user_id,
                            req.question,
                            sop_steps[:8],
                            full_answer,
                        )
                        state = sop_service.get_sop_state(req.session_id)
                        if state.get("exists"):
                            sop_record["current_step"] = state.get("current_step", 1)
                            sop_record["all_done"] = state.get("all_done", False)
                            for i, s in enumerate(sop_record.get("steps", [])):
                                if i < len(state.get("steps", [])):
                                    s["step_status"] = state["steps"][i].get("status", "pending")
                                    s["step_note"] = state["steps"][i].get("note", "")
                    except Exception as e:
                        logger.warning(f"save_version 失败: {e}")
                        sop_record = None

            # 自动从 Agent 回复中解析 SOP 状态更新意图并执行
            _auto_apply_sop_updates(req.session_id, full_answer, req.question)

            # 推送最新状态 + sop_version
            try:
                auto_state = sop_service.get_sop_state(req.session_id)
                if auto_state.get("exists"):
                    yield f"data: {json.dumps({'type': 'sop_state', 'state': auto_state}, ensure_ascii=False)}\n\n"
                    if sop_record:
                        # 重新注入更新后的状态
                        sop_record["current_step"] = auto_state.get("current_step", 1)
                        sop_record["all_done"] = auto_state.get("all_done", False)
                        for i, s in enumerate(sop_record.get("steps", [])):
                            if i < len(auto_state.get("steps", [])):
                                s["step_status"] = auto_state["steps"][i].get("status", "pending")
                                s["step_note"] = auto_state["steps"][i].get("note", "")
                        yield f"data: {json.dumps({'type': 'sop_version', 'sop': sop_record}, ensure_ascii=False)}\n\n"
            except Exception:
                pass

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


# 提报状态持久化
import fcntl as _fcntl
from pathlib import Path as _Path

_REPORT_STATE_FILE = _Path(__file__).resolve().parent.parent.parent / "data" / "report_submitted.json"

def _load_report_state() -> set:
    try:
        return set(json.loads(_REPORT_STATE_FILE.read_text("utf-8")))
    except: return set()

def _save_report_state(state: set):
    _REPORT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_STATE_FILE.write_text(json.dumps(list(state)), "utf-8")


@router.get("/report/submitted/{order_id}")
def check_report_submitted(order_id: str):
    return {"submitted": order_id in _load_report_state()}

@router.post("/report/submitted/{order_id}")
def mark_report_submitted(order_id: str):
    state = _load_report_state()
    state.add(order_id)
    _save_report_state(state)
    return {"submitted": True}
