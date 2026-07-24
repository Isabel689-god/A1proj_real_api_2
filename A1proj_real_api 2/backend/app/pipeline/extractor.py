"""大模型批量三元组抽取流水线主控。"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.db import get_session, init_db
from app.langchain.rag_chain import _mk_llm
from app.pipeline.prompts import TRIPLE_EXTRACTION_PROMPT_COMPACT
from app.pipeline.validator import Triple, TripleValidator
from app.pipeline.deduper import TripleDeduper
from app.pipeline.db_writer import TripleDBWriter

logger = logging.getLogger(__name__)


@dataclass
class ExtractResult:
    total_docs: int = 0
    raw_triples: int = 0
    valid_triples: int = 0
    unique_triples: int = 0
    entities_inserted: int = 0
    relations_inserted: int = 0
    errors: list[str] = field(default_factory=list)


class TripleExtractor:
    """批量从维修文档中抽取三元组 → 校验 → 消重 → 入库。"""

    def __init__(self, batch_size: int = 5):
        self.llm = _mk_llm(temperature=0.1, streaming=False)
        self.validator = TripleValidator()
        self.deduper = TripleDeduper()
        self.writer = TripleDBWriter()
        self.batch_size = batch_size

    def extract_from_documents(self, docs: list[dict]) -> ExtractResult:
        """主流程。"""
        result = ExtractResult(total_docs=len(docs))
        all_triples: list[Triple] = []

        # Phase 1: LLM 批量抽取
        for i in range(0, len(docs), self.batch_size):
            batch = docs[i:i + self.batch_size]
            text = "\n---\n".join(
                f"[{d.get('source', '?')}] {d.get('title', '')}: {d.get('content', '')}"
                for d in batch
            )
            source = batch[0].get("source", "unknown")
            try:
                raw = self.llm.invoke(
                    TRIPLE_EXTRACTION_PROMPT_COMPACT.format(document_text=text[:3000])
                )
                parsed = self._parse(raw.content if hasattr(raw, "content") else str(raw))
                for t in parsed:
                    t.source_doc = source
                    t.confidence = 0.7
                all_triples.extend(parsed)
                result.raw_triples += len(parsed)
            except Exception as e:
                result.errors.append(f"LLM error batch {i}: {e}")
                logger.warning(f"LLM 抽取失败 (batch {i}): {e}")

        # Phase 2: 校验
        valid, val_errors = self.validator.validate(all_triples)
        result.valid_triples = len(valid)
        result.errors.extend(val_errors)

        # Phase 3: 消重
        unique = self.deduper.dedup(valid)
        result.unique_triples = len(unique)

        # Phase 4: 入库
        stats = self.writer.insert_batch(unique)
        result.entities_inserted = stats["entities_inserted"]
        result.relations_inserted = stats["relations_inserted"]

        return result

    @staticmethod
    def _parse(text: str) -> list[Triple]:
        """解析 LLM 输出为 Triple 列表。"""
        triples: list[Triple] = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            triples.append(Triple(
                head_type=parts[0].strip(),
                head_name=parts[1].strip(),
                relation=parts[2].strip(),
                tail_type=parts[3].strip(),
                tail_name=parts[4].strip(),
            ))
        return triples
