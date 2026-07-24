"""动态知识库：用户案例、经验入库、审核、回答修正。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamicKnowledgeStore:
    def __init__(self):
        settings = get_settings()
        self.base = Path(settings.KNOWLEDGE_DIR)
        self.base.mkdir(parents=True, exist_ok=True)
        self.cases_path = self.base / settings.USER_CASES_JSON
        self.corrections_path = self.base / settings.CORRECTIONS_JSON

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 案例 ----------
    def list_cases(self, status: str | None = None) -> list[dict]:
        data = self._load_json(self.cases_path, {"cases": []})
        cases = data.get("cases", [])
        if status:
            cases = [c for c in cases if c.get("status") == status]
        return cases

    def add_case(
        self,
        title: str,
        content: str,
        device_model: str | None = None,
        tags: list[str] | None = None,
        author: str = "user",
        image_note: str | None = None,
    ) -> dict:
        case = {
            "id": f"case_{uuid.uuid4().hex[:12]}",
            "title": title,
            "content": content,
            "device_model": device_model,
            "tags": tags or [],
            "image_note": image_note,
            "author": author,
            "status": "pending",
            "created_at": _utc_now(),
            "reviewed_at": None,
            "reviewer": None,
            "review_comment": None,
        }
        data = self._load_json(self.cases_path, {"cases": []})
        data.setdefault("cases", []).append(case)
        self._save_json(self.cases_path, data)
        return case

    def review_case(
        self,
        case_id: str,
        approve: bool,
        reviewer: str = "admin",
        comment: str = "",
    ) -> dict:
        data = self._load_json(self.cases_path, {"cases": []})
        for case in data.get("cases", []):
            if case["id"] != case_id:
                continue
            case["status"] = "approved" if approve else "rejected"
            case["reviewed_at"] = _utc_now()
            case["reviewer"] = reviewer
            case["review_comment"] = comment
            self._save_json(self.cases_path, data)
            return case
        raise KeyError(f"案例不存在：{case_id}")

    def approved_cases_as_documents(self) -> list[dict]:
        docs = []
        for case in self.list_cases(status="approved"):
            content = case["content"]
            if case.get("image_note"):
                content = f"{content}\n\n【图片说明】{case['image_note']}"
            title = case["title"]
            if case.get("device_model"):
                title = f"{case['device_model']}｜{title}"
            docs.append({
                "id": case["id"],
                "title": title,
                "content": content,
                "source": "user_case",
                "tags": list(case.get("tags") or []) + ([case["device_model"]] if case.get("device_model") else []),
                "doc_type": "case",
                "status": "approved",
            })
        return docs

    # ---------- 回答修正 ----------
    def add_correction(
        self,
        question: str,
        wrong_answer: str,
        corrected_answer: str,
        related_doc_ids: list[str] | None = None,
        author: str = "admin",
    ) -> dict:
        item = {
            "id": f"fix_{uuid.uuid4().hex[:12]}",
            "question": question,
            "wrong_answer": wrong_answer,
            "corrected_answer": corrected_answer,
            "related_doc_ids": related_doc_ids or [],
            "author": author,
            "created_at": _utc_now(),
        }
        data = self._load_json(self.corrections_path, {"corrections": []})
        data.setdefault("corrections", []).append(item)
        self._save_json(self.corrections_path, data)
        return item

    def list_corrections(self) -> list[dict]:
        data = self._load_json(self.corrections_path, {"corrections": []})
        return data.get("corrections", [])

    def corrections_as_documents(self) -> list[dict]:
        docs = []
        for c in self.list_corrections():
            docs.append({
                "id": c["id"],
                "title": f"经验修正｜{c['question'][:40]}",
                "content": (
                    f"问题：{c['question']}\n"
                    f"错误回答：{c['wrong_answer']}\n"
                    f"修正回答：{c['corrected_answer']}"
                ),
                "source": "manual_correction",
                "tags": ["经验修正"],
                "doc_type": "correction",
                "status": "approved",
            })
        return docs

    def find_correction_for_question(self, question: str) -> dict | None:
        q = question.strip().lower()
        for c in self.list_corrections():
            if c["question"].strip().lower() in q or q in c["question"].strip().lower():
                return c
        return None

    # ---------- 手册上传申请 ----------
    def list_manual_requests(self, status: str | None = None) -> list[dict]:
        data = self._load_json(self.base / "manual_requests.json", {"requests": []})
        requests = data.get("requests", [])
        if status:
            requests = [r for r in requests if r.get("status") == status]
        return requests

    def add_manual_request(
        self,
        filename: str,
        file_size: int,
        applicant: str,
        description: str = "",
        device_model: str | None = None,
    ) -> dict:
        req = {
            "id": f"mreq_{uuid.uuid4().hex[:12]}",
            "filename": filename,
            "file_size": file_size,
            "applicant": applicant,
            "description": description,
            "device_model": device_model,
            "status": "pending",
            "created_at": _utc_now(),
            "reviewed_at": None,
            "reviewer": None,
            "review_comment": None,
        }
        data = self._load_json(self.base / "manual_requests.json", {"requests": []})
        data.setdefault("requests", []).append(req)
        self._save_json(self.base / "manual_requests.json", data)
        return req

    def review_manual_request(
        self,
        request_id: str,
        approve: bool,
        reviewer: str = "admin",
        comment: str = "",
    ) -> dict:
        data = self._load_json(self.base / "manual_requests.json", {"requests": []})
        for req in data.get("requests", []):
            if req["id"] != request_id:
                continue
            req["status"] = "approved" if approve else "rejected"
            req["reviewed_at"] = _utc_now()
            req["reviewer"] = reviewer
            req["review_comment"] = comment
            self._save_json(self.base / "manual_requests.json", data)
            return req
        raise KeyError(f"申请不存在：{request_id}")