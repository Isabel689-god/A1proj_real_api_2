"""权限组服务 — JSON 持久化，支持 CRUD。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings

DEFAULT_GROUPS = {
    "基础访客": {
        "description": "仅可对话和查看图谱",
        "permissions": ["chat", "view_graph"],
    },
    "维修人员": {
        "description": "可对话、提报工单",
        "permissions": ["chat", "submit_report"],
    },
    "管理人员": {
        "description": "全部功能权限，含用户管理和手册上传",
        "permissions": ["chat", "view_graph", "submit_report", "direct_upload", "update_graph", "audit_uploads", "request_upload"],
    },
}


class PermissionGroupService:
    def __init__(self):
        settings = get_settings()
        self._path = Path(settings.KNOWLEDGE_DIR) / "permission_groups.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_defaults()

    def _init_defaults(self):
        if not self._path.exists():
            self._save(DEFAULT_GROUPS)

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def _save(self, data: dict):
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_groups(self) -> dict[str, Any]:
        return self._load()

    def create_group(self, name: str, description: str, permissions: list[str]) -> bool:
        data = self._load()
        if name in data:
            return False
        data[name] = {"description": description, "permissions": permissions}
        self._save(data)
        return True

    def update_group(self, name: str, description: str, permissions: list[str]) -> bool:
        data = self._load()
        if name not in data:
            return False
        existing = data[name]
        data[name] = {"description": description, "permissions": permissions, "members": existing.get("members", [])}
        self._save(data)
        return True

    def delete_group(self, name: str) -> bool:
        data = self._load()
        if name not in data:
            return False
        del data[name]
        self._save(data)
        return True

    def get_group_permissions(self, name: str) -> list[str]:
        data = self._load()
        group = data.get(name, {})
        return group.get("permissions", [])


group_service = PermissionGroupService()
