"""SQLAlchemy ORM 模型：5 实体表 + 1 关系表 + 1 类型字典表。"""
from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.db.engine import Base


def _biz_id(prefix: str, name: str) -> str:
    h = hashlib.md5(name.strip().encode()).hexdigest()[:8]
    return f"{prefix}:{h}"


class Device(Base):
    __tablename__ = "device"
    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    model = Column(String(255), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class Component(Base):
    __tablename__ = "component"
    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class Fault(Base):
    __tablename__ = "fault"
    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    alarm_code = Column(String(100), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class FaultCause(Base):
    __tablename__ = "fault_cause"
    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class Solution(Base):
    __tablename__ = "solution"
    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    steps = Column(Text, default="")
    risk_level = Column(String(20), default="低")
    verified = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Relation(Base):
    __tablename__ = "relation"
    __table_args__ = (
        UniqueConstraint(
            "src_type", "src_id", "rel_type", "dst_type", "dst_id",
            name="uq_triple",
        ),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    src_type = Column(String(32), nullable=False, index=True)
    src_id = Column(String(64), nullable=False, index=True)
    rel_type = Column(String(128), nullable=False)
    dst_type = Column(String(32), nullable=False, index=True)
    dst_id = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, default=0.5)
    source_doc = Column(String(512), default="")
    created_at = Column(DateTime, server_default=func.now())


class EntityTypeDict(Base):
    __tablename__ = "entity_type_dict"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False)
    table_name = Column(String(64), nullable=False)
    display_name = Column(String(64), nullable=False)
