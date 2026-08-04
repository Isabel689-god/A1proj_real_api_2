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


class User(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    group_name = Column(String(64), default="访客组")
    extra_permissions = Column(Text, default="[]")
    is_online = Column(Integer, default=0)
    registered_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)


class Session(Base):
    __tablename__ = "sys_session"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), default="新对话")
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "sys_message"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class MaintenanceRecord(Base):
    __tablename__ = "sys_maintenance_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_model = Column(String(255), default="")
    fault_type = Column(String(255), default="")
    repair_date = Column(String(32), default="")
    technician = Column(String(64), default="")
    description = Column(Text, default="")
    solution = Column(Text, default="")
    parts_replaced = Column(Text, default="")
    status = Column(String(20), default="已完成")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
