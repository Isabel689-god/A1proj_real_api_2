import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db import get_session, User
from sqlalchemy import select, update, delete
from pathlib import Path
from app.core.config import get_settings


class UserService:
    """用户服务：MySQL 版，权限从 permission_groups.json 继承。"""

    def __init__(self):
        self.settings = get_settings()
        self._init_default_users()

    def _utc_now(self):
        return datetime.now(timezone.utc)

    def _load_groups(self) -> Dict[str, Any]:
        path = Path(self.settings.KNOWLEDGE_DIR) / "permission_groups.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _get_group_permissions(self, group: str, extra_json: str) -> List[str]:
        groups = self._load_groups()
        fallback_groups = {
            "访客组": ["chat"],
            "普通维修人员": ["chat", "submit_report", "request_upload"],
            "高级维修人员": ["chat", "submit_report", "direct_upload", "update_graph", "audit_uploads", "request_upload"],
            "管理组": ["chat", "submit_report", "direct_upload", "update_graph", "audit_uploads", "request_upload"],
        }
        base = groups.get(group, {}).get("permissions", fallback_groups.get(group, []))
        if "all" in base:
            return ["all"]
        try:
            extra = json.loads(extra_json) if extra_json else []
        except Exception:
            extra = []
        return list(set(base + extra))

    def _init_default_users(self):
        defaults = [
            ("admin", "admin", "管理组"),
            ("senior_01", "123", "高级维修人员"),
            ("emp_01", "123", "普通维修人员"),
            ("employee_01", "123", "普通维修人员"),
            ("intern_01", "123", "访客组"),
        ]
        s = get_session()
        try:
            existing = set(s.execute(select(User.username)).scalars().all())
            for username, password, group in defaults:
                if username not in existing:
                    s.add(User(username=username, password=password, group_name=group))
            s.commit()
        finally:
            s.close()

    def login(self, username: str, password: str) -> Dict[str, Any] | None:
        s = get_session()
        try:
            u = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if u and u.password == password:
                s.execute(update(User).where(User.username == username).values(
                    is_online=1, last_login=self._utc_now()))
                s.commit()
                permissions = self._get_group_permissions(u.group_name, u.extra_permissions or "[]")
                return {"username": u.username, "group": u.group_name, "permissions": permissions}
            return None
        finally:
            s.close()

    def logout(self, username: str):
        s = get_session()
        try:
            s.execute(update(User).where(User.username == username).values(is_online=0))
            s.commit()
        finally:
            s.close()

    def get_all_users(self) -> List[Dict[str, Any]]:
        s = get_session()
        try:
            users = s.execute(select(User).order_by(User.username)).scalars().all()
            return [{
                "username": u.username,
                "group": u.group_name,
                "registered_at": u.registered_at.isoformat() if u.registered_at else "",
                "is_online": bool(u.is_online),
                "permissions": self._get_group_permissions(u.group_name, u.extra_permissions or "[]"),
                "extra_permissions": json.loads(u.extra_permissions) if u.extra_permissions else [],
            } for u in users]
        finally:
            s.close()

    def add_user(self, username: str, password: str, group: str) -> bool:
        s = get_session()
        try:
            existing = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if existing:
                return False
            groups = self._load_groups()
            if group not in groups:
                return False
            s.add(User(username=username, password=password, group_name=group))
            s.commit()
            return True
        finally:
            s.close()

    def update_user_group(self, username: str, group: str) -> bool:
        s = get_session()
        try:
            groups = self._load_groups()
            if group not in groups:
                return False
            result = s.execute(update(User).where(User.username == username).values(group_name=group))
            s.commit()
            return result.rowcount > 0
        finally:
            s.close()

    def update_user_permissions(self, username: str, extra: List[str]) -> bool:
        s = get_session()
        try:
            result = s.execute(update(User).where(User.username == username).values(
                extra_permissions=json.dumps(extra, ensure_ascii=False)))
            s.commit()
            return result.rowcount > 0
        finally:
            s.close()

    def delete_user(self, username: str) -> bool:
        s = get_session()
        try:
            if username == "admin":
                return False
            result = s.execute(delete(User).where(User.username == username))
            s.commit()
            return result.rowcount > 0
        finally:
            s.close()


user_service = UserService()
