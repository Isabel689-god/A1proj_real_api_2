from fastapi import APIRouter, Depends
from app.core.config import get_settings
from app.knowledge.sync_service import KnowledgeSyncService
from app.api.v1.knowledge import verify_admin
import os
import time
from pathlib import Path

router = APIRouter(prefix="/monitor", tags=["系统监控"])


@router.get("/status", summary="获取系统整体运行状态")
def get_system_status(_=Depends(verify_admin)):
    settings = get_settings()
    sync_service = KnowledgeSyncService()
    state = sync_service._load_sync_state()

    # DashVector 向量检索（阿里云线上服务）
    dashvector_configured = bool(settings.DASHVECTOR_ENDPOINT and settings.DASHVECTOR_API_KEY)

    # 知识库统计
    doc_count = state.get("document_count", 0)
    manual_count = state.get("manual_count", 0)
    dynamic_count = state.get("dynamic_count", 0)
    pdf_count = state.get("pdf_count", 0)
    docx_count = state.get("docx_count", 0)

    # 文件路径状态
    data_dir_exists = Path(settings.DATA_DIR).exists()
    knowledge_dir_exists = Path(settings.KNOWLEDGE_DIR).exists()

    # 大模型配置状态（仅校验配置，不实际调用避免消耗token）
    llm_configured = bool(settings.api_key and settings.api_key != "your_api_key_here")
    embedding_configured = llm_configured  # 共用同一套API

    # 计算运行时长（近似值，从进程启动时间算）
    try:
        import psutil
        process = psutil.Process(os.getpid())
        uptime_seconds = time.time() - process.create_time()
        uptime_str = f"{int(uptime_seconds // 3600)}小时 {int((uptime_seconds % 3600) // 60)}分钟"
    except ImportError:
        uptime_str = "未安装 psutil，无法获取运行时长"

    return {
        "system": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug_mode": settings.DEBUG,
            "uptime": uptime_str,
            "data_dir": settings.DATA_DIR,
            "knowledge_dir": settings.KNOWLEDGE_DIR
        },
        "knowledge_base": {
            "total_documents": doc_count,
            "manual_documents": manual_count,
            "dynamic_documents": dynamic_count,
            "pdf_files": pdf_count,
            "docx_files": docx_count,
            "dashvector_configured": dashvector_configured,
            "last_sync_files": list(state.get("files", {}).keys()),
            "sync_errors": state.get("errors", [])
        },
        "services": {
            "llm_configured": llm_configured,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "embedding_configured": embedding_configured,
            "embedding_model": settings.EMBEDDING_MODEL,
            "data_dir_exists": data_dir_exists,
            "knowledge_dir_exists": knowledge_dir_exists
        },
        "config": {
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "rag_top_k": settings.RAG_TOP_K,
            "allow_fallback": settings.LLM_ALLOW_FALLBACK
        }
    }


@router.post("/test-llm", summary="测试大模型连通性")
def test_llm_connection(_=Depends(verify_admin)):
    """实际发送一条极简请求测试大模型是否可用"""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from app.langchain.rag_chain import get_llm
        llm = get_llm()
        prompt = ChatPromptTemplate.from_messages([("human", "ping")])
        result = llm.invoke(prompt.invoke({})).content or ""
        return {
            "success": True,
            "provider": f"langchain:{llm.model_name}",
            "response": result[:50] + "..." if len(result) > 50 else result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }