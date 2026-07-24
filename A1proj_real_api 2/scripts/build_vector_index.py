"""使用真实 Embedding API + FAISS 构建向量索引。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.rag.faiss_index import FaissIndexManager  # noqa: E402


def main() -> None:
    settings = get_settings()
    path = settings.knowledge_path
    if not path.exists():
        raise FileNotFoundError(f"请先运行 build_maintenance_knowledge.py 或 sync_and_index.py：{path}")
    docs = json.loads(path.read_text(encoding="utf-8"))
    print(f"加载知识 {len(docs)} 条，调用真实 Embedding API…")
    info = FaissIndexManager().build(docs)
    print("FAISS 索引完成：", info)


if __name__ == "__main__":
    main()
