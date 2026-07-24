"""检查知识库和向量索引是否可用。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = ROOT / "backend" / "app" / "data" / "knowledge" / "maintenance_knowledge.json"
INDEX_PATH = ROOT / "backend" / "app" / "data" / "knowledge" / "vector_index.json"
REQUIRED_FIELDS = {"id", "title", "content", "source"}


def main() -> None:
    if not KNOWLEDGE_PATH.exists():
        raise FileNotFoundError(f"知识库不存在：{KNOWLEDGE_PATH}")

    docs = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    if not isinstance(docs, list):
        raise ValueError("知识库顶层必须是列表。")

    ids = set()
    for idx, doc in enumerate(docs, start=1):
        missing = REQUIRED_FIELDS - set(doc.keys())
        if missing:
            raise ValueError(f"第 {idx} 条知识缺少字段：{missing}")
        if doc["id"] in ids:
            raise ValueError(f"知识 id 重复：{doc['id']}")
        ids.add(doc["id"])

    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if len(index) != len(docs):
            raise ValueError("向量索引数量与知识库数量不一致。")
        print(f"校验通过：知识库 {len(docs)} 条，向量索引 {len(index)} 条。")
    else:
        print(f"校验通过：知识库 {len(docs)} 条。尚未生成向量索引，可运行 scripts/build_vector_index.py。")


if __name__ == "__main__":
    main()
