"""从 data/ 目录同步维修手册到知识库（兼容旧命令）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.knowledge.sync_service import KnowledgeSyncService  # noqa: E402


def main() -> None:
    result = KnowledgeSyncService().sync()
    print(f"知识库已同步：{result['document_count']} 条")
    print(f"输出：{result['knowledge_path']}")


if __name__ == "__main__":
    main()
