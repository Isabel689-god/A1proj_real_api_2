"""从 data/ 目录增量同步维修手册，构建可迭代知识库与知识图谱。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from time import time

from app.core.config import get_settings
from app.knowledge.document_parser import assign_ids, file_md5, parse_manual_file
from app.knowledge.dynamic_store import DynamicKnowledgeStore
from app.knowledge.graph_builder import build_graph_from_documents


class KnowledgeSyncService:
    SUPPORTED = {".pdf", ".docx", ".xls", ".xlsx"}

    def __init__(self):
        self.settings = get_settings()
        self.knowledge_dir = Path(self.settings.KNOWLEDGE_DIR)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_path = self.settings.knowledge_path
        self.sync_state_path = self.knowledge_dir / self.settings.SYNC_STATE_JSON
        self.graph_path = self.settings.graph_path
        self.dynamic = DynamicKnowledgeStore()

    def _manual_dirs(self) -> list[Path]:
        dirs = []
        for d in [Path(self.settings.DATA_DIR), Path(self.settings.DATA_DIR_FALLBACK)]:
            if d.exists():
                dirs.append(d)
        return dirs

    def _list_manual_files(self) -> list[Path]:
        files: dict[str, Path] = {}
        for d in self._manual_dirs():
            for p in d.iterdir():
                if p.is_file() and p.suffix.lower() in self.SUPPORTED:
                    files[p.name] = p
        return sorted(files.values(), key=lambda x: x.name)

    def _load_sync_state(self) -> dict:
        if not self.sync_state_path.exists():
            return {"files": {}, "document_count": 0, "errors": []}
        return json.loads(self.sync_state_path.read_text(encoding="utf-8"))

    def _save_sync_state(self, state: dict) -> None:
        self.sync_state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_manual_documents(self) -> tuple[list[dict], dict, list[str]]:
        state = self._load_sync_state()
        file_hashes: dict[str, str] = dict(state.get("files", {}))
        errors: list[str] = []
        all_docs: list[dict] = []

        for path in self._list_manual_files():
            try:
                md5 = file_md5(path)
                prev = file_hashes.get(path.name)
                raw = parse_manual_file(path)
                docs = assign_ids(raw, path.name)
                all_docs.extend(docs)
                file_hashes[path.name] = md5
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        state["files"] = file_hashes
        state["pdf_count"] = sum(1 for n in file_hashes if n.lower().endswith(".pdf"))
        state["docx_count"] = sum(1 for n in file_hashes if n.lower().endswith(".docx"))
        state["xls_count"] = sum(1 for n in file_hashes if n.lower().endswith((".xls", ".xlsx")))
        state["errors"] = errors
        return all_docs, state, errors

    def sync(self, force: bool = False) -> dict[str, Any]:
        """同步手册 + 已审核案例 + 修正条目，写入 knowledge JSON、图谱与 DashVector 向量索引。"""
        manual_docs, state, errors = self._load_manual_documents()
        dynamic_docs = (
            self.dynamic.approved_cases_as_documents()
            + self.dynamic.corrections_as_documents()
        )
        documents = manual_docs + dynamic_docs
        state["document_count"] = len(documents)
        state["manual_count"] = len(manual_docs)
        state["dynamic_count"] = len(dynamic_docs)
        state["updated_at"] = time()

        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_path.write_text(
            json.dumps(documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        graph = build_graph_from_documents(documents)
        self.graph_path.write_text(
            json.dumps(graph, ensure_ascii=False),
            encoding="utf-8",
        )
        self._save_sync_state(state)

        # 重建 DashVector 向量索引 + 刷新对话缓存
        try:
            from app.langchain.vector_store import DashVectorStore

            DashVectorStore().save(documents)
            from app.api.v1.chat import reload

            reload()
        except Exception as exc:
            errors.append(f"向量索引重建失败: {exc}")

        return {
            "document_count": len(documents),
            "manual_count": len(manual_docs),
            "dynamic_count": len(dynamic_docs),
            "files": list(state.get("files", {}).keys()),
            "errors": errors,
            "knowledge_path": str(self.knowledge_path),
            "graph_path": str(self.graph_path),
        }

    def load_all_documents(self) -> list[dict]:
        if not self.knowledge_path.exists():
            self.sync(force=True)
        return json.loads(self.knowledge_path.read_text(encoding="utf-8"))
