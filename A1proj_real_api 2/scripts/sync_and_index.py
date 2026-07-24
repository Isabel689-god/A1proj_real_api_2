"""一键：从 data/ 同步手册 → 构建知识图谱 → 真实 API 向量索引。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.knowledge.sync_service import KnowledgeSyncService  # noqa: E402
from app.rag.faiss_index import FaissIndexManager  # noqa: E402


def main() -> None:
    sync = KnowledgeSyncService()
    result = sync.sync()
    print("同步完成：", result)
    docs = sync.load_all_documents()
    print(f"共 {len(docs)} 条知识，开始调用真实 Embedding API 构建 FAISS…")
    info = FaissIndexManager().build(docs)
    print("向量索引完成：", info)


if __name__ == "__main__":
    main()
