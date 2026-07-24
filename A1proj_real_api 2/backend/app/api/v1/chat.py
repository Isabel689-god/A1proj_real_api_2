"""聊天 API：异步端点，流式 LLM → SSE 逐句输出。"""
from __future__ import annotations

import asyncio, json, logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.chat_history import InMemoryChatMessageHistory

from app.langchain.rag_chain import RAGChain
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
            None, _rag.retrieve, req.question, req.device_model, req.image_url
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

            if sources:
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
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
