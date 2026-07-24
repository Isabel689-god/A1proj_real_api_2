import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import get_settings


class UserService:
    # 角色基础权限定义
    BASE_PERMISSIONS = {
        "intern": ["chat", "view_graph"],
        "employee": ["chat", "view_graph", "submit_report", "request_upload"],
        "senior": ["chat", "view_graph", "submit_report", "direct_upload", "update_graph", "view_intern_logs",
                   "audit_uploads"],
        "admin": ["all"]
    }

    def __init__(self):
        self.settings = get_settings()
        self.users_path = self.settings.users_path
        self.users_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_default_users()

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_users(self) -> Dict[str, Any]:
        if not self.users_path.exists():
            return {}
        try:
            return json.loads(self.users_path.read_text(encoding="utf-8"))
        except:
            return {}

    def _save_users(self, data: Dict[str, Any]) -> None:
        self.users_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _init_default_users(self):
        users = self._load_users()
        defaults = {
            "admin": {"password": "admin", "role": "admin", "extra_permissions": [], "registered_at": self._utc_now(),
                      "is_online": False},
            "senior_01": {"password": "123", "role": "senior", "extra_permissions": [],
                          "registered_at": self._utc_now(), "is_online": False},
            "emp_01": {"password": "123", "role": "employee", "extra_permissions": [], "registered_at": self._utc_now(),
                       "is_online": False},
            "intern_01": {"password": "123", "role": "intern", "extra_permissions": [],
                          "registered_at": self._utc_now(), "is_online": False}
        }
        changed = False
        for k, v in defaults.items():
            if k not in users:
                users[k] = v
                changed = True
        if changed:
            self._save_users(users)

    def get_user_permissions(self, role: str, extra_permissions: List[str]) -> List[str]:
        base = self.BASE_PERMISSIONS.get(role, [])
        if "all" in base:
            return ["all"]
        # 合并基础权限和额外权限，去重
        return list(set(base + extra_permissions))

    def login(self, username: str, password: str) -> Dict[str, Any] | None:
        users = self._load_users()
        user = users.get(username)
        if user and user.get("password") == password:
            # 更新在线状态
            user["is_online"] = True
            self._save_users(users)

            permissions = self.get_user_permissions(user["role"], user.get("extra_permissions", []))
            return {
                "username": username,
                "role": user["role"],
                "permissions": permissions
            }
        return None

    def logout(self, username: str):
        users = self._load_users()
        if username in users:
            users[username]["is_online"] = False
            self._save_users(users)

    def get_all_users(self) -> List[Dict[str, Any]]:
        users = self._load_users()
        res = []
        for uname, udata in users.items():
            res.append({
                "username": uname,
                "role": udata.get("role"),
                "registered_at": udata.get("registered_at"),
                "is_online": udata.get("is_online", False),
                "permissions": self.get_user_permissions(udata.get("role"), udata.get("extra_permissions", [])),
                "extra_permissions": udata.get("extra_permissions", [])
            })
        return res

    def add_user(self, username: str, password: str, role: str) -> bool:
        users = self._load_users()
        if username in users:
            return False
        if role not in self.BASE_PERMISSIONS:
            return False
        users[username] = {
            "password": password,
            "role": role,
            "extra_permissions": [],
            "registered_at": self._utc_now(),
            "is_online": False
        }
        self._save_users(users)
        return True

    def update_user_permissions(self, username: str, extra_permissions: List[str]) -> bool:
        users = self._load_users()
        if username not in users:
            return False
        users[username]["extra_permissions"] = extra_permissions
        self._save_users(users)
        return True

    def delete_user(self, username: str) -> bool:
        users = self._load_users()
        if username in users and username != "admin":
            del users[username]
            self._save_users(users)
            return True
        return False


user_service = UserService()