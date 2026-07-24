"""三元组后置校验：类型合法性、格式完整性、实体名清洗。"""
from __future__ import annotations

from dataclasses import dataclass
from app.db.entity_type import valid_types

_VALID_TYPES = set(valid_types())


@dataclass
class Triple:
    head_type: str
    head_name: str
    relation: str
    tail_type: str
    tail_name: str
    source_doc: str = ""
    confidence: float = 0.5

    @property
    def line(self) -> str:
        return f"{self.head_type}|{self.head_name}|{self.relation}|{self.tail_type}|{self.tail_name}"


class TripleValidator:
    def __init__(self, min_rel_len: int = 2, max_rel_len: int = 80):
        self.min_rel_len = min_rel_len
        self.max_rel_len = max_rel_len

    def validate(self, triples: list[Triple]) -> tuple[list[Triple], list[str]]:
        valid: list[Triple] = []
        errors: list[str] = []
        for i, t in enumerate(triples):
            errs = self._check_one(t)
            if errs:
                errors.append(f"[{i}] {t.line} -> {'; '.join(errs)}")
            else:
                valid.append(t)
        return valid, errors

    def _check_one(self, t: Triple) -> list[str]:
        errs = []
        if t.head_type not in _VALID_TYPES:
            errs.append(f"illegal head type: {t.head_type}")
        if t.tail_type not in _VALID_TYPES:
            errs.append(f"illegal tail type: {t.tail_type}")
        if not t.head_name or not t.head_name.strip():
            errs.append("empty head name")
        else:
            t.head_name = _clean_name(t.head_name)
        if not t.tail_name or not t.tail_name.strip():
            errs.append("empty tail name")
        else:
            t.tail_name = _clean_name(t.tail_name)
        rel = t.relation.strip()
        if len(rel) < self.min_rel_len:
            errs.append(f"relation too short: '{rel}'")
        if len(rel) > self.max_rel_len:
            errs.append(f"relation too long: {len(rel)} chars")
        t.relation = rel
        return errs


def _clean_name(name: str) -> str:
    name = name.strip()
    name = name.replace("  ", " ")
    name = name.replace("（", "(").replace("）", ")")
    name = name.replace("，", ",")
    return name
