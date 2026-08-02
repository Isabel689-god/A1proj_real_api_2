"""会话持久化服务 — MySQL 存储。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db import get_session, Session, Message
from sqlalchemy import select, update, delete


class SessionService:
    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    def _now_dt(self):
        return datetime.now(timezone.utc)

    def save(self, session_id: str, user_id: str, messages: list[dict], title: str = ""):
        s = get_session()
        try:
            existing = s.execute(select(Session).where(Session.session_id == session_id)).scalar_one_or_none()
            if existing:
                s.execute(update(Session).where(Session.session_id == session_id).values(
                    title=title or existing.title,
                    message_count=len(messages),
                    updated_at=self._now_dt(),
                ))
                s.execute(delete(Message).where(Message.session_id == session_id))
            else:
                s.add(Session(
                    session_id=session_id, user_id=user_id,
                    title=title or "新对话", message_count=len(messages),
                    created_at=self._now_dt(), updated_at=self._now_dt(),
                ))
            for m in messages:
                s.add(Message(
                    session_id=session_id,
                    role=m.get("role", "user"),
                    content=m.get("content", ""),
                ))
            s.commit()
        finally:
            s.close()

    def load(self, session_id: str, user_id: str | None = None) -> dict | None:
        s = get_session()
        try:
            stmt = select(Session).where(Session.session_id == session_id)
            if user_id:
                stmt = stmt.where(Session.user_id == user_id)
            ses = s.execute(stmt).scalar_one_or_none()
            if not ses:
                return None
            msgs = s.execute(
                select(Message).where(Message.session_id == session_id).order_by(Message.id)
            ).scalars().all()
            return {
                "session_id": ses.session_id,
                "user_id": ses.user_id,
                "title": ses.title,
                "messages": [{"role": m.role, "content": m.content} for m in msgs],
                "message_count": ses.message_count,
                "created_at": ses.created_at.strftime("%Y-%m-%d %H:%M") if ses.created_at else "",
                "updated_at": ses.updated_at.strftime("%Y-%m-%d %H:%M") if ses.updated_at else "",
            }
        finally:
            s.close()

    def list_by_user(self, user_id: str) -> list[dict]:
        s = get_session()
        try:
            sessions = s.execute(
                select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
            ).scalars().all()
            return [{
                "session_id": ses.session_id,
                "title": ses.title,
                "message_count": ses.message_count,
                "created_at": ses.created_at.strftime("%Y-%m-%d %H:%M") if ses.created_at else "",
                "updated_at": ses.updated_at.strftime("%Y-%m-%d %H:%M") if ses.updated_at else "",
            } for ses in sessions]
        finally:
            s.close()

    def delete(self, session_id: str, user_id: str | None = None) -> bool:
        s = get_session()
        try:
            if user_id:
                ses = s.execute(
                    select(Session).where(Session.session_id == session_id, Session.user_id == user_id)
                ).scalar_one_or_none()
                if not ses:
                    return False
            s.execute(delete(Message).where(Message.session_id == session_id))
            stmt = delete(Session).where(Session.session_id == session_id)
            if user_id:
                stmt = stmt.where(Session.user_id == user_id)
            result = s.execute(stmt)
            s.commit()
            return result.rowcount > 0
        finally:
            s.close()


session_service = SessionService()
