import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import get_settings, _find_env
from app.core.llm_provider import test_llm_connection as run_llm_connection_test
from app.db import get_session
from app.knowledge.sync_service import KnowledgeSyncService
from app.api.v1.knowledge import verify_admin
import time
from datetime import datetime
from pathlib import Path

router = APIRouter(prefix="/monitor", tags=["系统监控"])
START_TIME = time.time()
logger = logging.getLogger(__name__)


def _fmt_dt(ts: float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _fmt_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}天 {hours}小时 {minutes}分钟"
    return f"{hours}小时 {minutes}分钟"


def _latest_manual_change(settings, files: dict) -> float | None:
    mtimes = []
    for name in files:
        for base in (Path(settings.DATA_DIR), Path(settings.DATA_DIR_FALLBACK)):
            p = base / name
            if p.exists():
                mtimes.append(p.stat().st_mtime)
                break
    return max(mtimes) if mtimes else None


def _check_database() -> dict:
    started = time.perf_counter()
    session = None
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "label": "正常",
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        logger.exception("Database health check failed")
        return {
            "status": "connection_failed",
            "label": "连接失败",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "reason": "数据库无法连接或账号权限不足",
        }
    finally:
        if session is not None:
            session.close()


def _safe_dir_status(path: Path) -> dict:
    if not path.exists():
        return {"status": "missing", "label": "缺失"}
    if not path.is_dir():
        return {"status": "invalid", "label": "路径异常"}
    return {"status": "healthy", "label": "存在"}


@router.get("/status", summary="获取系统整体运行状态")
def get_system_status(_=Depends(verify_admin)):
    settings = get_settings()
    sync_service = KnowledgeSyncService()
    state = sync_service._load_sync_state()  # 仅用于最后同步时间/错误

    # DashVector / FAISS
    dashvector_configured = bool(settings.DASHVECTOR_ENDPOINT and settings.DASHVECTOR_API_KEY)
    faiss_path = Path(settings.KNOWLEDGE_DIR) / "faiss_index" / "index.faiss"
    faiss_available = faiss_path.exists()

    # 实时统计：直接从 knowledge.json 和物理文件计算
    knowledge_path = Path(settings.KNOWLEDGE_DIR) / settings.KNOWLEDGE_JSON
    if knowledge_path.exists():
        try:
            all_docs = json.loads(knowledge_path.read_text(encoding="utf-8"))
        except Exception:
            all_docs = []
        doc_count = len(all_docs)
        manual_count = len([d for d in all_docs if d.get("source")])
        dynamic_count = doc_count - manual_count
    else:
        doc_count = manual_count = dynamic_count = 0

    physical_files = sync_service._list_manual_files()
    physical_pdf_count = sum(1 for p in physical_files if p.suffix.lower() == ".pdf")
    pdf_count = physical_pdf_count
    docx_count = sum(1 for p in physical_files if p.suffix.lower() == ".docx")
    synced_files = len(state.get("files", {}))  # 已同步的手册文件数

    # 文件路径状态
    data_dir_status = _safe_dir_status(Path(settings.DATA_DIR))
    knowledge_dir_status = _safe_dir_status(Path(settings.KNOWLEDGE_DIR))
    knowledge_file = Path(settings.KNOWLEDGE_DIR) / settings.KNOWLEDGE_JSON
    graph_file = Path(settings.KNOWLEDGE_DIR) / settings.KNOWLEDGE_GRAPH_JSON

    if dashvector_configured and doc_count > 0 and not state.get("errors"):
        vector_index = {
            "status": "healthy",
            "label": "存在/正常",
            "reason": "DashVector 已配置，知识库文档可用于检索",
        }
    elif dashvector_configured and doc_count > 0:
        vector_index = {
            "status": "unavailable",
            "label": "需检查",
            "reason": "同步状态存在错误：" + "；".join(state.get("errors", [])[:2]),
        }
    elif faiss_available:
        vector_index = {
            "status": "healthy",
            "label": "本地正常",
            "reason": "FAISS 本地向量索引已就绪，知识库文档可用于检索",
        }
    elif not dashvector_configured:
        vector_index = {
            "status": "ok",
            "label": "关键词检索",
            "reason": "DashVector 未配置，使用本地关键词搜索。安装 sentence-transformers 可启用向量语义搜索",
        }
    else:
        vector_index = {
            "status": "not_created",
            "label": "未创建",
            "reason": "知识库文档为空，尚未建立可用索引",
        }

    # 大模型配置状态（仅校验配置，不实际调用避免消耗token）
    llm_configured = bool(settings.api_key and settings.api_key != "your_api_key_here")
    embedding_configured = llm_configured  # 共用同一套API
    database_status = _check_database()

    uptime_seconds = time.time() - START_TIME
    uptime_str = _fmt_uptime(uptime_seconds)

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug_mode": settings.DEBUG,
            "uptime": uptime_str,
            "started_at": _fmt_dt(START_TIME),
            "data_dir": settings.DATA_DIR,
            "knowledge_dir": settings.KNOWLEDGE_DIR
        },
        "knowledge_base": {
            "total_documents": doc_count,
            "manual_documents": manual_count,
            "dynamic_documents": dynamic_count,
            "pdf_files": physical_pdf_count,
            "docx_files": docx_count,
            "physical_files": len(physical_files),
            "document_chunks": doc_count,
            "dashvector_configured": dashvector_configured,
            "vector_index": vector_index,
            "vector_entries": doc_count if vector_index["status"] in ("healthy", "ok") else 0,
            "last_sync_files": list(state.get("files", {}).keys()),
            "sync_errors": state.get("errors", [])
        },
        "services": {
            "llm_configured": llm_configured,
            "embedding_configured": embedding_configured,
            "embedding_model": settings.EMBEDDING_MODEL,
            "database": database_status,
            "data_dir": data_dir_status,
            "knowledge_dir": knowledge_dir_status,
            "data_dir_exists": data_dir_status["status"] == "healthy",
            "knowledge_dir_exists": knowledge_dir_status["status"] == "healthy",
        },
        "config": {
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "rag_top_k": settings.RAG_TOP_K,
            "allow_fallback": settings.LLM_ALLOW_FALLBACK
        },
        "operations": {
            "last_sync_result": f"{doc_count} 条文档，{manual_count} 条手册切片，{dynamic_count} 条动态知识",
            "last_sync_at": _fmt_dt(state.get("updated_at") or (knowledge_file.stat().st_mtime if knowledge_file.exists() else None)),
            "last_manual_change": f"{len(state.get('files', {}))} 个手册文件已记录",
            "last_manual_change_at": _fmt_dt(_latest_manual_change(settings, state.get("files", {}))),
            "knowledge_file": "存在" if knowledge_file.exists() else "缺失",
            "knowledge_file_updated_at": _fmt_dt(knowledge_file.stat().st_mtime if knowledge_file.exists() else None),
            "graph_file": "存在" if graph_file.exists() else "缺失",
            "graph_file_updated_at": _fmt_dt(graph_file.stat().st_mtime if graph_file.exists() else None),
        }
    }


@router.post("/test-llm", summary="测试大模型连通性")
def test_llm_connection(_=Depends(verify_admin)):
    """实际发送一条极简请求测试大模型是否可用"""
    return run_llm_connection_test()


@router.get("/model-config")
def get_model_config(_=Depends(verify_admin)):
    """获取当前模型配置。"""
    s = get_settings()
    def _hint(key_val: str) -> str:
        if not key_val: return ""
        return key_val[:5] + "***" + key_val[-3:] if len(key_val) > 8 else "***"
    return {
        "chat": {
            "provider": s.LLM_PROVIDER,
            "model": s.LLM_MODEL,
            "base_url": getattr(s, 'LLM_BASE_URL', ''),
            "has_key": bool(s.api_key),
            "key_hint": _hint(s.api_key),
        },
        "vision": {
            "model": s.VISION_MODEL,
            "base_url": getattr(s, 'VISION_BASE_URL', ''),
            "has_key": bool(s.vision_api_key),
            "key_hint": _hint(s.vision_api_key),
        },
        "embedding": {
            "model": s.EMBEDDING_MODEL,
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "has_key": bool(getattr(s, 'VISION_API_KEY', '') or s.api_key),
            "key_hint": _hint(getattr(s, 'VISION_API_KEY', '') or s.api_key),
        },
        "asr": {
            "provider": s.ASR_PROVIDER,
            "model": s.ASR_MODEL,
            "base_url": getattr(s, 'ASR_BASE_URL', ''),
            "has_key": bool(s.ASR_API_KEY),
            "key_hint": _hint(s.ASR_API_KEY),
        },
        "tts": {
            "provider": s.TTS_PROVIDER,
            "model": s.TTS_MODEL,
            "base_url": getattr(s, 'TTS_BASE_URL', ''),
            "has_key": bool(s.TTS_API_KEY),
            "key_hint": _hint(s.TTS_API_KEY),
        }
    }


@router.put("/model-config")
def update_model_config(payload: dict, _=Depends(verify_admin)):
    """更新模型配置。type: 'chat'（对话模型）或 'vision'（视觉模型）。"""
    model_type = (payload.get("type") or "chat").strip()
    model = (payload.get("model") or "").strip()

    if model_type == "vision":
        return _update_vision_model(model, base_url=payload.get("base_url", ""), api_key=payload.get("api_key", ""), provider=payload.get("provider", ""))
    if model_type == "embedding":
        return _update_embedding_model(model, base_url=payload.get("base_url", ""), api_key=payload.get("api_key", ""), provider=payload.get("provider", ""))
    if model_type == "asr":
        return _update_asr_model(model, base_url=payload.get("base_url", ""), api_key=payload.get("api_key", ""), provider=payload.get("provider", ""))
    if model_type == "tts":
        return _update_tts_model(model, base_url=payload.get("base_url", ""), api_key=payload.get("api_key", ""), provider=payload.get("provider", ""))
    return _update_chat_model(model, provider=payload.get("provider", ""), base_url=payload.get("base_url", ""), api_key=payload.get("api_key", ""))


def _update_chat_model(model: str, provider: str = "", base_url: str = "", api_key: str = ""):
    kv = {"LLM_MODEL": model}
    if provider: kv["LLM_PROVIDER"] = provider
    if base_url: kv["LLM_BASE_URL"] = base_url
    if api_key: kv["LLM_API_KEY"] = api_key
    _write_env(kv)

    get_settings.cache_clear()
    s = get_settings()
    return {
        "success": True,
        "chat": {"provider": s.LLM_PROVIDER, "model": s.LLM_MODEL,
                 "base_url": getattr(s, 'LLM_BASE_URL', ''), "has_key": bool(s.api_key)},
    }


def _update_vision_model(model: str, base_url: str = "", api_key: str = "", provider: str = ""):
    kv = {"VISION_MODEL": model}
    if provider: kv["VISION_PROVIDER"] = provider
    if base_url: kv["VISION_BASE_URL"] = base_url
    if api_key: kv["VISION_API_KEY"] = api_key
    _write_env(kv)

    get_settings.cache_clear()
    s = get_settings()
    return {
        "success": True,
        "vision": {"model": s.VISION_MODEL,
                   "base_url": getattr(s, 'VISION_BASE_URL', ''), "has_key": bool(s.vision_api_key)},
    }


def _update_embedding_model(model: str, base_url: str = "", api_key: str = "", provider: str = ""):
    kv = {"EMBEDDING_MODEL": model}
    if provider: kv["EMBEDDING_PROVIDER"] = provider
    if api_key: kv["VISION_API_KEY"] = api_key
    _write_env(kv)

    get_settings.cache_clear()
    s = get_settings()
    return {
        "success": True,
        "embedding": {"model": s.EMBEDDING_MODEL,
                      "has_key": bool(getattr(s, 'VISION_API_KEY', '') or s.api_key)},
    }


def _update_asr_model(model: str, base_url: str = "", api_key: str = "", provider: str = ""):
    kv = {"ASR_MODEL": model}
    if provider: kv["ASR_PROVIDER"] = provider
    if base_url: kv["ASR_BASE_URL"] = base_url
    if api_key: kv["ASR_API_KEY"] = api_key
    _write_env(kv)

    get_settings.cache_clear()
    s = get_settings()
    return {
        "success": True,
        "asr": {"provider": s.ASR_PROVIDER, "model": s.ASR_MODEL,
                "base_url": getattr(s, 'ASR_BASE_URL', ''), "has_key": bool(s.ASR_API_KEY)},
    }


def _update_tts_model(model: str, base_url: str = "", api_key: str = "", provider: str = ""):
    kv = {"TTS_MODEL": model}
    if provider: kv["TTS_PROVIDER"] = provider
    if base_url: kv["TTS_BASE_URL"] = base_url
    if api_key: kv["TTS_API_KEY"] = api_key
    _write_env(kv)

    get_settings.cache_clear()
    s = get_settings()
    return {
        "success": True,
        "tts": {"provider": s.TTS_PROVIDER, "model": s.TTS_MODEL,
                "base_url": getattr(s, 'TTS_BASE_URL', ''), "has_key": bool(s.TTS_API_KEY)},
    }


def _write_env(kv: dict):
    """更新 .env 中的键值对。"""
    env_path = _find_env()
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    for key, value in kv.items():
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
