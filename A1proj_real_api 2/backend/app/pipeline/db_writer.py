"""分表入库：按实体类型写入对应 MySQL 表。"""
from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError

from app.db import (
    Component, Device, Fault, FaultCause, Solution,
    Relation, EntityType, _biz_id, get_session,
)
from app.pipeline.validator import Triple

logger = logging.getLogger(__name__)

# 类型 → 模型映射
TYPE_TO_MODEL = {
    EntityType.device: Device,
    EntityType.component: Component,
    EntityType.fault: Fault,
    EntityType.fault_cause: FaultCause,
    EntityType.solution: Solution,
}


class TripleDBWriter:
    """将校验消重后的三元组写入 MySQL。"""

    def __init__(self):
        self.stats = {"entities_inserted": 0, "entities_skipped": 0,
                      "relations_inserted": 0, "relations_skipped": 0,
                      "errors": 0}

    def insert_batch(self, triples: list[Triple]) -> dict:
        """批量写入，每条三元组一个事务。"""
        session = get_session()
        try:
            for t in triples:
                try:
                    self._insert_one(session, t)
                except IntegrityError:
                    session.rollback()
                    self.stats["relations_skipped"] += 1
                except Exception as e:
                    session.rollback()
                    self.stats["errors"] += 1
                    logger.warning(f"写入失败 [{t.line}]: {e}")
            session.commit()
        finally:
            session.close()
        return dict(self.stats)

    def _insert_one(self, session, t: Triple) -> None:
        """单条三元组入库：查或插头尾实体，再插关系。"""
        src_model = TYPE_TO_MODEL[EntityType(t.head_type)]
        dst_model = TYPE_TO_MODEL[EntityType(t.tail_type)]

        src = self._get_or_create(session, src_model, t.head_type, t.head_name)
        dst = self._get_or_create(session, dst_model, t.tail_type, t.tail_name)

        rel = Relation(
            src_type=t.head_type, src_id=src.biz_id,
            rel_type=t.relation,
            dst_type=t.tail_type, dst_id=dst.biz_id,
            confidence=t.confidence, source_doc=t.source_doc,
        )
        session.add(rel)
        session.flush()
        self.stats["relations_inserted"] += 1

    def _get_or_create(self, session, model, etype: str, name: str):
        """查实体 → 存在则返回，不存在则创建。"""
        obj = session.query(model).filter_by(name=name).first()
        if obj:
            self.stats["entities_skipped"] += 1
            return obj
        obj = model(biz_id=_biz_id(etype, name), name=name)
        session.add(obj)
        session.flush()
        self.stats["entities_inserted"] += 1
        return obj
