"""三元组消重：实体去重 + 三元组去重。"""
from __future__ import annotations

from app.pipeline.validator import Triple


class TripleDeduper:
    def dedup(self, triples: list[Triple]) -> list[Triple]:
        entity_map: dict[tuple[str, str], str] = {}
        for t in triples:
            kh = (t.head_type, t.head_name)
            if kh not in entity_map:
                entity_map[kh] = t.head_name
            else:
                t.head_name = entity_map[kh]
            kt = (t.tail_type, t.tail_name)
            if kt not in entity_map:
                entity_map[kt] = t.tail_name
            else:
                t.tail_name = entity_map[kt]
        seen: set[tuple] = set()
        unique: list[Triple] = []
        for t in triples:
            key = (t.head_type, t.head_name, t.relation, t.tail_type, t.tail_name)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique
