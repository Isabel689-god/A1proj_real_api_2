"""Neo4j AuraDB 知识图谱直连服务 — 替换 Windows 桥接。

直接从 WSL 后端查询 Neo4j AuraDB 云实例，
查询节点/关系并输出 ECharts 兼容格式。
"""
from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import get_settings

# ── Neo4j 标签 → 前端 category 映射 ──
_LABEL_CATEGORY_MAP: dict[str, str] = {
    "Device":      "device",
    "Component":   "component",
    "Fault":       "fault",
    "FaultCause":  "fault_cause",
    "Solution":    "solution",
    "Document":    "document",
    "Tag":         "tag",
    "Parameter":   "parameter",
    "__Entity__":  "entity",
}

_CATEGORY_COLORS: dict[str, str] = {
    "device":      "#4a90d9",
    "component":   "#52c41a",
    "fault":       "#ff5f66",
    "fault_cause": "#f0b44c",
    "solution":    "#20c7c7",
    "document":    "#8ba4c7",
    "tag":         "#d7a34d",
    "parameter":   "#a78bfa",
    "entity":      "#9ca3af",
}


class Neo4jService:
    """Neo4j AuraDB 直连查询服务。"""

    def __init__(self) -> None:
        settings = get_settings()
        import os
        self._uri = os.environ.get("neo4j_uri", "")
        self._user = os.environ.get("neo4j_username", "")
        self._password = os.environ.get("neo4j_password", "")
        self._database = os.environ.get("neo4j_database", "neo4j")
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
        return self._driver

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def health_check(self) -> bool:
        """验证 AuraDB 连接是否正常。"""
        try:
            self.driver.verify_connectivity()
            return True
        except (ServiceUnavailable, AuthError, OSError):
            return False

    # ═══════════ 全量图谱 ═══════════

    def get_full_graph(self, entity_type: str | None = None) -> dict:
        """全量图谱数据，返回 ECharts 兼容格式。"""
        with self.driver.session(database=self._database) as session:
            nodes = self._query_nodes(session, entity_type)
            node_ids = {n["id"] for n in nodes}
            edges = self._query_edges(session, node_ids)

            # 度数
            degree: dict[str, int] = {}
            for e in edges:
                degree[e["source"]] = degree.get(e["source"], 0) + 1
                degree[e["target"]] = degree.get(e["target"], 0) + 1
            for n in nodes:
                n["symbolSize"] = min(60, 15 + degree.get(n["id"], 0) * 3)

            # categories
            cats_present = {n["category"] for n in nodes}
            categories = [
                {"name": c, "itemStyle": {"color": _CATEGORY_COLORS.get(c, "#9ca3af")}}
                for c in sorted(cats_present)
            ]

            return {
                "code": 200,
                "data": {
                    "nodes": nodes,
                    "edges": edges,
                    "categories": categories,
                },
            }

    # ═══════════ 节点详情 ═══════════

    def get_node_detail(self, node_id: str) -> dict | None:
        """单个节点详情 + 所有邻接关系。"""
        with self.driver.session(database=self._database) as session:
            # 查节点本身
            result = session.run(
                "MATCH (n) WHERE elementId(n) = $id OR n.name = $id OR n.doc_id = $id "
                "RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props "
                "LIMIT 1",
                {"id": node_id},
            )
            record = result.single()
            if record is None:
                return None

            lbls = record["labels"]
            props = record["props"]
            eid = record["eid"]
            category = _label_to_category(lbls)

            node = {
                "id": eid,
                "name": props.get("name") or props.get("title") or props.get("doc_id", eid),
                "category": category,
                "description": props.get("description", ""),
            }

            # 查邻接关系
            rel_result = session.run(
                "MATCH (n)-[r]-(m) WHERE elementId(n) = $id "
                "RETURN type(r) AS rel_type, "
                "       startNode(r) = n AS outgoing, "
                "       labels(m) AS mlabels, properties(m) AS mprops, "
                "       elementId(m) AS meid "
                "LIMIT 50",
                {"id": eid},
            )
            neighbors: list[dict] = []
            for rec in rel_result:
                neighbors.append({
                    "direction": "out" if rec["outgoing"] else "in",
                    "relation": rec["rel_type"],
                    "entity_type": _label_to_category(rec["mlabels"]),
                    "entity_id": rec["meid"],
                    "entity_name": rec["mprops"].get("name") or rec["mprops"].get("title", ""),
                })

            return {"node": node, "neighbors": neighbors}

    # ═══════════ 图谱扩展（检索增强） ═══════════

    def expand_doc_ids(self, seed_ids: list[str], limit: int = 5) -> list[tuple[str, int]]:
        """给定种子文档 ID，通过图谱共享关系找到相关文档。

        共享故障/部件/标签的文档视为相关，按共享数量排序。
        返回 (doc_id, strength) 元组列表，strength 为共享实体数。
        """
        if not seed_ids:
            return []
        with self.driver.session(database=self._database) as session:
            result = session.run(
                "MATCH (d:Document)-[:DESCRIBES_FAULT|HAS_COMPONENT|TAGGED]->(shared)"
                "<-[:DESCRIBES_FAULT|HAS_COMPONENT|TAGGED]-(other:Document) "
                "WHERE d.doc_id IN $seed_ids "
                "  AND other.doc_id <> d.doc_id "
                "  AND NOT other.doc_id IN $seed_ids "
                "RETURN DISTINCT other.doc_id AS doc_id, "
                "       count(DISTINCT shared) AS strength "
                "ORDER BY strength DESC "
                "LIMIT $limit",
                {"seed_ids": seed_ids, "limit": limit},
            )
            return [(rec["doc_id"], rec["strength"]) for rec in result]

    # ═══════════ 统计 ═══════════

    def get_stats(self) -> dict:
        """各类型节点与关系数量统计。"""
        with self.driver.session(database=self._database) as session:
            node_stats = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC"
            )
            stats = {rec["label"]: rec["cnt"] for rec in node_stats}
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()
            stats["relation"] = rel_count["cnt"] if rel_count else 0
            return stats

    # ═══════════ 内部方法 ═══════════

    @staticmethod
    def _query_nodes(session, entity_type: str | None) -> list[dict]:
        """查询所有节点。"""
        if entity_type:
            neo4j_label = _category_to_label(entity_type)
            query = (
                f"MATCH (n:`{neo4j_label}`) "
                "RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props"
            )
        else:
            query = (
                "MATCH (n) "
                "RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props"
            )

        result = session.run(query)
        nodes: list[dict] = []
        for record in result:
            lbls = record["labels"]
            props = record["props"]
            eid = record["eid"]
            category = _label_to_category(lbls)
            name = props.get("name") or props.get("title") or props.get("doc_id", eid)
            nodes.append({
                "id": eid,
                "name": (name[:60] + "…") if len(name) > 60 else name,
                "category": category,
            })
        return nodes

    @staticmethod
    def _query_edges(session, valid_ids: set[str]) -> list[dict]:
        """查询涉及 valid_ids 中节点的边。"""
        result = session.run(
            "MATCH (a)-[r]->(b) "
            "RETURN elementId(a) AS src_id, type(r) AS rel_type, elementId(b) AS dst_id"
        )
        edges: list[dict] = []
        for record in result:
            src, dst = record["src_id"], record["dst_id"]
            if src in valid_ids and dst in valid_ids:
                edges.append({
                    "source": src,
                    "relation": _rel_display_name(record["rel_type"]),
                    "target": dst,
                    "confidence": 1.0,
                })
        return edges


# ── 标签 ↔ 前端 category 互转 ──

def _label_to_category(labels: list[str]) -> str:
    """Neo4j 标签列表 → 前端 category 名。"""
    for lbl in labels:
        cat = _LABEL_CATEGORY_MAP.get(lbl)
        if cat:
            return cat
    # fallback: 用小写首标签
    return labels[0].lower() if labels else "entity"


def _category_to_label(category: str) -> str:
    """前端 category → Neo4j 标签。"""
    reverse = {v: k for k, v in _LABEL_CATEGORY_MAP.items()}
    return reverse.get(category, category.capitalize())


def _rel_display_name(rel_type: str) -> str:
    """Neo4j 关系类型 → 中文显示名。"""
    _map = {
        "INCLUDES":        "包含文档",
        "HAS_COMPONENT":   "包含部件",
        "TAGGED":          "标注",
        "DESCRIBES_FAULT": "描述故障",
        "HAS_FAULT":       "存在故障",
        "CAUSED_BY":       "由…引起",
        "SOLVED_BY":       "解决方案",
        "RELATED_TO":      "关联",
        "DESCRIBED_IN":    "在文档中描述",
        "AFFECTS_PARAMETER": "影响参数",
    }
    return _map.get(rel_type, rel_type.replace("_", " ").title())
