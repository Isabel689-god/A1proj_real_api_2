"""系统配置。从 .env 读取真实大模型 API 配置。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def _find_env() -> Path:
    """按优先级找 .env：当前目录 → 自动推算 → 默认位置。"""
    candidates = [
        Path.cwd() / ".env",
        PROJECT_ROOT / ".env",
        Path(".") / ".env",
    ]
    for p in candidates:
        if p.exists():
            return p
    return PROJECT_ROOT / ".env"  # 默认，不存在也不报错

_ENV_PATH = _find_env()


class Settings(BaseSettings):
    """所有配置项统一管理。敏感信息从 .env 读取。

    LLM_API_KEY / LLM_BASE_URL 优先使用显式字段；
    未设置时回退到旧的 ZHIPU_* 环境变量（向后兼容）。
    """

    APP_NAME: str = "A1 Project Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── 大模型配置（OpenAI 兼容接口） ──
    LLM_PROVIDER: str = "dashscope"
    LLM_MODEL: str = "qwen3.7-plus"
    LLM_API_KEY: str = Field(
        default="",
        description="OpenAI-compatible API key",
    )
    LLM_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="OpenAI-compatible base URL",
    )
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_ALLOW_FALLBACK: bool = False

    # 向后兼容：如果 LLM_API_KEY 为空，从 ZHIPU_API_KEY 读取
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = ""

    # DashScope 备用 Key（千问模型切换时自动使用）
    DASHSCOPE_API_KEY: str = ""

    @property
    def api_key(self) -> str:
        # DashScope provider 优先用 DASHSCOPE_API_KEY
        if self.DASHSCOPE_API_KEY and "dashscope" in (self.LLM_BASE_URL or ""):
            return self.DASHSCOPE_API_KEY.strip()
        return (self.LLM_API_KEY or self.ZHIPU_API_KEY or self.DASHSCOPE_API_KEY).strip()

    @property
    def api_base(self) -> str:
        return (self.LLM_BASE_URL or self.ZHIPU_BASE_URL).strip()

    # ── MySQL（阿里云 RDS 知识图谱存储） ──
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "ruanjiandata"

    @property
    def mysql_dsn(self) -> str:
        pwd = self.MYSQL_PASSWORD
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{pwd}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}"
            f"/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    # ── 向量嵌入 ──
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_BATCH_SIZE: int = 10

    # ── 视觉理解（可独立配置，默认复用大模型配置）──
    VISION_MODEL: str = "qwen-vl-plus"
    VISION_API_KEY: str = ""
    VISION_BASE_URL: str = ""

    # GLM 视觉模型 Key
    GLM_API_KEY: str = ""

    @property
    def vision_api_key(self) -> str:
        # GLM 模型优先用 GLM_API_KEY
        if self.GLM_API_KEY and (self.VISION_MODEL or "").lower().startswith("glm"):
            return self.GLM_API_KEY.strip()
        return (self.VISION_API_KEY or self.api_key).strip()

    @property
    def vision_api_base(self) -> str:
        return (self.VISION_BASE_URL or self.api_base).strip()

    # ── DashVector 向量检索（阿里云）──
    DASHVECTOR_ENDPOINT: str = ""
    DASHVECTOR_API_KEY: str = ""
    DASHVECTOR_COLLECTION: str = "a1proj_knowledge"
    DASHVECTOR_DIMENSION: int = 1024

    @property
    def dashvector_config(self) -> dict:
        return {
            "endpoint": self.DASHVECTOR_ENDPOINT,
            "api_key": self.DASHVECTOR_API_KEY,
            "collection": self.DASHVECTOR_COLLECTION,
            "dimension": self.DASHVECTOR_DIMENSION,
        }

    # ── 手册数据目录 ──
    DATA_DIR: str = str(PROJECT_ROOT / "data")
    DATA_DIR_FALLBACK: str = str(PROJECT_ROOT / "backend" / "app" / "data" / "raw")

    # ── 知识库存储 ──
    KNOWLEDGE_DIR: str = str(PROJECT_ROOT / "backend" / "app" / "data" / "knowledge")
    KNOWLEDGE_JSON: str = "maintenance_knowledge.json"
    KNOWLEDGE_GRAPH_JSON: str = "knowledge_graph.json"
    SYNC_STATE_JSON: str = "sync_state.json"
    USER_CASES_JSON: str = "user_cases.json"
    CORRECTIONS_JSON: str = "corrections.json"
    USERS_JSON: str = "users.json"

    # ── 检索 ──
    RAG_TOP_K: int = 5
    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 120

    # ── 管理员 ──
    ADMIN_TOKEN: str = "admin-change-me"

    class Config:
        env_file = str(_ENV_PATH)
        env_file_encoding = "utf-8"
        extra = "ignore"

    # ── 派生路径属性 ──

    @property
    def knowledge_path(self) -> Path:
        return Path(self.KNOWLEDGE_DIR) / self.KNOWLEDGE_JSON

    @property
    def graph_path(self) -> Path:
        return Path(self.KNOWLEDGE_DIR) / self.KNOWLEDGE_GRAPH_JSON

    @property
    def users_path(self) -> Path:
        return Path(self.KNOWLEDGE_DIR) / self.USERS_JSON


@lru_cache
def get_settings() -> Settings:
    return Settings()
