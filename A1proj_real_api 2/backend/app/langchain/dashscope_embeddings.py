"""
DashScope OpenAI-compatible embeddings wrapper.

Bypasses the ``openai`` Python client (which tokenizes ``input`` into integers
that DashScope rejects) and sends raw text strings via ``requests`` instead.
"""
from __future__ import annotations

import logging
from typing import List

import requests
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DashScopeCompatibleEmbeddings(Embeddings):
    """Embedding model backed by DashScope's OpenAI-compatible endpoint.

    Uses ``requests`` to POST raw text to ``/embeddings``, avoiding the
    ``openai`` client's automatic tiktoken tokenization that DashScope rejects.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        batch_size: int = 10,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.EMBEDDING_MODEL
        self.api_key = api_key or settings.api_key
        self.base_url = (base_url or settings.api_base).rstrip("/")
        self.batch_size = max(1, min(batch_size, 10))  # DashScope batch limit is 10

    def _call_api(self, inputs: List[str]) -> List[List[float]]:
        """POST one or more texts and return their embedding vectors."""
        url = f"{self.base_url}/embeddings"
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": inputs},
            timeout=60,
        )
        if resp.status_code != 200:
            detail = resp.text[:500]
            logger.error(
                "DashScope embeddings API error %d: %s", resp.status_code, detail
            )
            raise RuntimeError(
                f"DashScope embeddings API returned {resp.status_code}: {detail}"
            )
        data = resp.json()
        # Sorted by index — DashScope returns them in request order
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in items]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if not texts:
            return []
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            all_embeddings.extend(self._call_api(batch))
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self._call_api([text])[0]
