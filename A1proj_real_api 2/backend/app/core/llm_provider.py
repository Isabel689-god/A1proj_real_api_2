"""Centralized OpenAI-compatible LLM provider utilities."""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float | None = None, streaming: bool = False, max_tokens: int | None = None) -> ChatOpenAI:
    """Create a configured ChatOpenAI-compatible model instance."""
    settings = get_settings()
    if not settings.api_key:
        raise RuntimeError("LLM_API_KEY 未配置")
    if not settings.api_base:
        raise RuntimeError("LLM_BASE_URL 未配置")
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.api_key,
        openai_api_base=settings.api_base,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        streaming=streaming,
    )


def sanitize_llm_error(exc: Exception) -> tuple[str, str]:
    """Return a coarse error type and a user-safe Chinese reason."""
    raw = str(exc)
    lower = raw.lower()
    if "未配置" in raw:
        return "not_configured", raw
    if "401" in raw or "unauthorized" in lower or "invalid api key" in lower:
        return "auth_failed", "API Key 无效或权限不足"
    if "timeout" in lower or "timed out" in lower:
        return "timeout", "模型接口响应超时"
    if "connection" in lower or "connect" in lower or "network" in lower:
        return "connection_failed", "无法连接模型接口"
    if "429" in raw or "rate limit" in lower:
        return "rate_limited", "模型接口限流或额度不足"
    return "service_error", "模型服务异常"


def test_llm_connection() -> dict[str, Any]:
    """Send a tiny real request and return a sanitized status payload."""
    settings = get_settings()
    if not settings.api_key or not settings.api_base:
        return {
            "success": False,
            "status": "not_configured",
            "model": settings.LLM_MODEL,
            "provider": settings.LLM_PROVIDER,
            "latency_ms": None,
            "error_type": "not_configured",
            "error": "大模型 API Key 或 Base URL 未配置",
        }
    started = time.perf_counter()
    try:
        llm = get_llm(max_tokens=16)
        resp = llm.invoke([HumanMessage(content="ping")])
        latency_ms = round((time.perf_counter() - started) * 1000)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {
            "success": True,
            "status": "healthy",
            "model": settings.LLM_MODEL,
            "provider": settings.LLM_PROVIDER,
            "latency_ms": latency_ms,
            "response": (content or "")[:80],
        }
    except Exception as exc:
        logger.exception("LLM connectivity test failed")
        error_type, safe_error = sanitize_llm_error(exc)
        return {
            "success": False,
            "status": error_type,
            "model": settings.LLM_MODEL,
            "provider": settings.LLM_PROVIDER,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error_type": error_type,
            "error": safe_error,
        }
