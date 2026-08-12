import logging
import os
import threading

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)
app = FastAPI(title=get_settings().APP_NAME, version=get_settings().APP_VERSION)


@app.on_event("startup")
def startup_init_db():
    """初始化 MySQL 连接并建表（幂等）。"""
    try:
        from app.db import init_db as _init_db
        _init_db()
        logger.info("MySQL 知识图谱数据库已就绪。")
    except Exception as exc:
        logger.warning(f"MySQL 初始化跳过（图谱查询将回退到 JSON）：{exc}")


@app.on_event("startup")
def startup_sync_knowledge():
    """启动时在后台检测 data/ 手册变更并同步知识库，避免阻塞服务器启动。"""
    import json
    from pathlib import Path

    try:
        from app.knowledge.document_parser import file_md5
        from app.knowledge.sync_service import KnowledgeSyncService

        settings = get_settings()
        sync = KnowledgeSyncService()
        state_path = Path(settings.KNOWLEDGE_DIR) / settings.SYNC_STATE_JSON
        manuals = sync._list_manual_files()
        if not manuals:
            logger.warning(
                "未在 data/ 或 raw/ 发现手册文件，请将 PDF/DOCX 放入项目 data/ 目录。"
            )
            return

        current = {p.name: file_md5(p) for p in manuals}
        old = {}
        if state_path.exists():
            old = json.loads(state_path.read_text(encoding="utf-8")).get("files", {})
        if current != old:
            logger.info("检测到手册变更，后台开始同步知识库与知识图谱...")

            def _sync_background():
                try:
                    sync.sync()
                    logger.info("后台知识库同步完成。")
                except Exception as e:
                    logger.warning(f"后台知识库同步失败：{e}")

            thread = threading.Thread(target=_sync_background, daemon=True)
            thread.start()
        else:
            logger.info("手册无变更，跳过知识库同步。")
    except Exception as exc:
        logger.warning(f"启动时知识库检测跳过：{exc}")


# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


# 托管前端页面
@app.get("/")
async def read_index():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "kg_visualization.html")
    )


@app.get("/kg")
async def read_kg_page():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "kg_visualization.html")
    )
