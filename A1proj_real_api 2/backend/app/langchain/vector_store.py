"""
DashVector 向量库封装。
使用阿里云 DashVector 替代 FAISS，线上向量检索，无需本地索引。
"""
from __future__ import annotations

from typing import Any

from langchain_community.vectorstores import DashVector
from langchain_core.documents import Document

from app.core.config import get_settings
from app.langchain.dashscope_embeddings import DashScopeCompatibleEmbeddings


def _get_embeddings() -> DashScopeCompatibleEmbeddings:
    settings = get_settings()
    return DashScopeCompatibleEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.api_key,
        base_url=settings.api_base,
    )


def _documents_from_knowledge(documents: list[dict[str, Any]]) -> list[Document]:
    """将知识库 dict 列表转为 LangChain Document 列表。"""
    result = []
    for doc in documents:
        text = f"{doc.get('title', '')}\n{doc.get('content', '')}"
        metadata = {
            "id": doc.get("id", ""),
            "title": doc.get("title", ""),
            "source": doc.get("source", ""),
            "tags": doc.get("tags", []),
            "score": doc.get("score", 0.0),
        }
        result.append(Document(page_content=text, metadata=metadata))
    return result


class DashVectorStore:
    """封装 LangChain DashVector store，提供 save/search 操作。"""

    def __init__(self):
        self.settings = get_settings()
        cfg = self.settings.dashvector_config
        self._store: DashVector | None = None
        self._broken: bool = False

    def save(self, documents: list[dict[str, Any]]) -> int:
        """将文档写入 DashVector 集合。"""
        docs = _documents_from_knowledge(documents)
        if not docs:
            raise ValueError("无文档可建索引。")
        self._store = DashVector.from_documents(
            docs, _get_embeddings(), **self.settings.dashvector_config
        )
        return len(docs)

    def search(
        self,
        query: str,
        documents: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """向量相似度搜索。"""
        if self._broken:
            return []
        if self._store is None:
            try:
                self._store = self._lazy_init(documents)
            except Exception:
                self._broken = True
                return []
        docs = self._store.similarity_search_with_score(query, k=top_k)
        results = []
        for d, score in docs:
            meta = d.metadata
            results.append({
                "id": meta.get("id", ""),
                "title": meta.get("title", ""),
                "content": d.page_content,
                "source": meta.get("source", ""),
                "tags": meta.get("tags", []),
                "vector_score": float(score),
            })
        return results

    def _lazy_init(self, documents: list[dict[str, Any]] | None) -> DashVector:
        """懒初始化：有文档则建索引，否则直接连已有集合。"""
        if documents:
            return self.save_and_return(documents)
        return DashVector(
            _get_embeddings(), **self.settings.dashvector_config
        )

    def save_and_return(self, documents: list[dict[str, Any]]) -> DashVector:
        docs = _documents_from_knowledge(documents)
        if not docs:
            raise ValueError("无文档可建索引。")
        return DashVector.from_documents(
            docs, _get_embeddings(), **self.settings.dashvector_config
        )


dashvector_store = DashVectorStore()
