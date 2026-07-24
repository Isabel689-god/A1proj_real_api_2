"""三元组抽取流水线。"""
from app.pipeline.extractor import TripleExtractor, ExtractResult
from app.pipeline.validator import Triple, TripleValidator
from app.pipeline.deduper import TripleDeduper
from app.pipeline.db_writer import TripleDBWriter

__all__ = [
    "TripleExtractor", "ExtractResult",
    "Triple", "TripleValidator", "TripleDeduper", "TripleDBWriter",
]
