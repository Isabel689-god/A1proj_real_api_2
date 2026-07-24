"""MySQL 知识图谱查询服务 — 聚合 5 实体表 + 关系表，输出 ECharts 格式。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text

from app.db import get_session, EntityType


_ECHARTS_CATEGORIES = [
    {"name": "device",      "itemStyle": {"color": "#4a90d9"}},
    {"name": "component",   "itemStyle": {"color": "#52c41a"}},
    {"name": "fault",       "itemStyle": {"color": "#ff4d4f"}},
    {"name": "fault_cause", "itemStyle": {"color": "#faad14"}},
    {"name": "solution",    "itemStyle": {"color": "#13c2c2"}},
]

_CATEGORY_NAMES = {c["name"] for c in _ECHARTS_CATEGORIES}


class GraphDBService:
    """MySQL 知识图谱读取服务。"""

    def get_full_graph(self, entity_type: str | None = None) -> dict:
        """全量图谱数据。entity_type 为空时返回全部，否则只返回该类型节点。"""
        session = get_session()
        try:
            nodes = self._collect_nodes(session, entity_type)
            all_biz_ids = {n["id"] for n in nodes}

            # 只拉涉及已存在节点的边
            edges = self._collect_edges(session, all_biz_ids)

            # 度数计算（用于节点大小）
            degree = defaultdict(int)
            for e in edges:
                degree[e["source"]] += 1
                degree[e["target"]] += 1

            for n in nodes:
                n["symbolSize"] = min(60, 15 + degree.get(n["id"], 0) * 3)

            # 只保留有对应节点的 categories
            cats_present = {n["category"] for n in nodes}
            categories = [c for c in _ECHARTS_CATEGORIES if c["name"] in cats_present]

            return {
                "code": 200,
                "data": {
                    "nodes": nodes,
                    "edges": edges,
                    "categories": categories,
                }
            }
        finally:
            session.close()

    def get_node_detail(self, biz_id: str) -> dict | None:
        """单个节点详情 + 所有邻接关系。"""
        session = get_session()
        try:
            # 确定节点类型
            node = None
            for etype, table in _TYPE_TO_TABLE.items():
                row = session.execute(
                    text(f"SELECT biz_id, name, description FROM {table} WHERE biz_id = :bid"),
                    {"bid": biz_id}
                ).fetchone()
                if row:
                    node = {"id": row[0], "name": row[1], "category": etype,
                            "description": row[2] or ""}
                    break
            if not node:
                return None

            # 邻接关系
            edges = session.execute(
                text(
                    "SELECT src_type, src_id, rel_type, dst_type, dst_id, confidence "
                    "FROM relation WHERE src_id = :bid OR dst_id = :bid"
                ),
                {"bid": biz_id}
            ).fetchall()

            neighbors = []
            for e in edges:
                if e[1] == biz_id:
                    direction = "out"
                    other_type, other_id = e[3], e[4]
                else:
                    direction = "in"
                    other_type, other_id = e[0], e[1]
                neighbors.append({
                    "direction": direction, "relation": e[2],
                    "entity_type": other_type, "entity_id": other_id,
                    "confidence": e[5],
                })

            return {"node": node, "neighbors": neighbors}
        finally:
            session.close()

    def get_stats(self) -> dict:
        """各类型实体与关系数量。"""
        session = get_session()
        try:
            stats = {}
            for etype, table in _TYPE_TO_TABLE.items():
                cnt = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                stats[etype] = cnt
            rel_cnt = session.execute(
                text("SELECT COUNT(*) FROM relation")
            ).scalar()
            stats["relation"] = rel_cnt
            return stats
        finally:
            session.close()

    # ═══════════ 内部方法 ═══════════

    @staticmethod
    def _collect_nodes(session, entity_type: str | None) -> list[dict]:
        nodes = []
        for etype, table in _TYPE_TO_TABLE.items():
            if entity_type and etype != entity_type:
                continue
            rows = session.execute(
                text(f"SELECT biz_id, name FROM {table}")
            ).fetchall()
            for r in rows:
                nodes.append({"id": r[0], "name": r[1], "category": etype})
        return nodes

    @staticmethod
    def _collect_edges(session, valid_ids: set[str]) -> list[dict]:
        rows = session.execute(
            text(
                "SELECT src_id, rel_type, dst_id, confidence "
                "FROM relation ORDER BY confidence DESC"
            )
        ).fetchall()
        edges = []
        for r in rows:
            if r[0] in valid_ids and r[2] in valid_ids:
                edges.append({
                    "source": r[0], "relation": r[1],
                    "target": r[2], "confidence": r[3],
                })
        return edges


# ── 辅助 ──

_TYPE_TO_TABLE = {
    "device": "device",
    "component": "component",
    "fault": "fault",
    "fault_cause": "fault_cause",
    "solution": "solution",
}
