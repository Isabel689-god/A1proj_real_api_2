"""本地 FAISS 向量库，无需云服务。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.config import get_settings
from app.langchain.vector_store import _get_embeddings, _documents_from_knowledge


class LocalVectorStore:
    """FAISS 本地向量索引。"""

    def __init__(self):
        self.settings = get_settings()
        self._index_dir = Path(self.settings.KNOWLEDGE_DIR) / "faiss_index"
        self._store: FAISS | None = None

    def _index_path(self) -> Path:
        return self._index_dir / "index.faiss"

    def save(self, documents: list[dict[str, Any]]) -> int:
        docs = _documents_from_knowledge(documents)
        if not docs:
            return 0
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._store = FAISS.from_documents(docs, _get_embeddings())
        self._store.save_local(str(self._index_dir))
        return len(docs)

    def search(
        self,
        query: str,
        documents: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self._store is None:
            if self._index_path().exists():
                self._store = FAISS.load_local(
                    str(self._index_dir),
                    _get_embeddings(),
                    allow_dangerous_deserialization=True,
                )
            elif documents:
                self.save(documents)
            else:
                return []
        results = self._store.similarity_search_with_score(query, k=top_k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]


_local_store: LocalVectorStore | None = None


def get_local_store() -> LocalVectorStore:
    global _local_store
    if _local_store is None:
        _local_store = LocalVectorStore()
    return _local_store
