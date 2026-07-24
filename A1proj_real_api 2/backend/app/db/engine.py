"""SQLAlchemy 引擎 + 会话工厂。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_engine(
            s.mysql_dsn,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            echo=False,
        )
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """创建所有表（幂等）。"""
    Base.metadata.create_all(bind=get_engine())
