"""知识图谱查询：故障定位、关联文档扩展。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


class KnowledgeGraphService:
    def __init__(self):
        self.path = get_settings().graph_path
        self._graph: dict | None = None

    def _load(self) -> dict:
        if self._graph is None:
            if not self.path.exists():
                self._graph = {"nodes": [], "edges": []}
            else:
                self._graph = json.loads(self.path.read_text(encoding="utf-8"))
        return self._graph

    def reload(self) -> None:
        self._graph = None

    def expand_doc_ids(self, doc_ids: list[str], limit: int = 8) -> list[str]:
        """通过图谱邻居扩展相关文档 id。"""
        graph = self._load()
        nodes = {n["id"]: n for n in graph.get("nodes", [])}
        # doc node id 形如 doc:xxx
        doc_nodes = {n["id"]: n for n in graph.get("nodes", []) if n.get("type") == "document"}
        id_by_doc = {n.get("label", ""): nid for nid, n in doc_nodes.items()}

        related: list[str] = []
        seen = set(doc_ids)

        for edge in graph.get("edges", []):
            src, dst, rel = edge.get("source"), edge.get("target"), edge.get("relation")
            for did in list(doc_ids):
                dn = f"doc:{did}" if not str(did).startswith("doc:") else did
                if src == dn or dst == dn:
                    other = dst if src == dn else src
                    on = nodes.get(other, {})
                    if on.get("type") == "document":
                        # 从 doc node 反查真实 id：label 对应 title，需匹配 maintenance id
                        pass
                    # 找同 tag/component 的其它文档
                    if on.get("type") in {"tag", "component", "fault", "device_model"}:
                        for e2 in graph.get("edges", []):
                            if e2.get("source") == other or e2.get("target") == other:
                                cand = e2.get("target") if e2.get("source") == other else e2.get("source")
                                cn = nodes.get(cand, {})
                                if cn.get("type") == "document":
                                    # 文档节点 label 含 title，用 maintenance id 需从 source 字段关联
                                    label = cn.get("label", "")
                                    for real_id in doc_ids:
                                        if label and real_id in label:
                                            continue
                                    # 简化：用节点 id 后缀匹配
                                    real = cand.replace("doc:", "", 1)
                                    if real not in seen:
                                        related.append(real)
                                        seen.add(real)
                                    if len(related) >= limit:
                                        return related[:limit]

        # 更直接：同 device_model / 同 tag
        for did in doc_ids:
            dn = f"doc:{did}"
            for edge in graph.get("edges", []):
                if edge.get("source") != dn and edge.get("target") != dn:
                    continue
                neighbor = edge.get("target") if edge.get("source") == dn else edge.get("source")
                n = nodes.get(neighbor, {})
                if n.get("type") != "tag":
                    continue
                tag = n.get("label")
                for e2 in graph.get("edges", []):
                    if tag and n.get("id") in (e2.get("source"), e2.get("target")):
                        other_doc = e2.get("target") if e2.get("source") == n.get("id") else e2.get("source")
                        on = nodes.get(other_doc, {})
                        if on.get("type") == "document":
                            # 从 maintenance 知识库 id 存在 doc 节点 id 中
                            rid = other_doc.replace("doc:", "", 1)
                            if rid not in seen and rid != did:
                                related.append(rid)
                                seen.add(rid)
                            if len(related) >= limit:
                                return related[:limit]
        return related[:limit]

    def fault_localization(self, keywords: list[str], device_model: str | None = None) -> dict[str, Any]:
        """根据关键词在图谱中定位可能故障与相关文档。"""
        graph = self._load()
        nodes = graph.get("nodes", [])
        hits: list[dict] = []
        kw_lower = [k.lower() for k in keywords if k]

        for node in nodes:
            label = (node.get("label") or "").lower()
            if not any(k in label for k in kw_lower):
                continue
            if device_model and device_model.lower() not in label:
                # 设备过滤稍宽松：仅对 device 类型严格
                if node.get("type") == "device_model" and device_model.lower() not in label:
                    continue
            hits.append(node)

        # 关联文档
        doc_titles: list[str] = []
        node_map = {n["id"]: n for n in nodes}
        hit_ids = {h["id"] for h in hits}
        for edge in graph.get("edges", []):
            if edge.get("source") in hit_ids or edge.get("target") in hit_ids:
                other = edge.get("target") if edge.get("source") in hit_ids else edge.get("source")
                on = node_map.get(other, {})
                if on.get("type") == "document":
                    doc_titles.append(on.get("label", ""))

        return {
            "matched_nodes": hits[:20],
            "related_documents": list(dict.fromkeys(doc_titles))[:15],
        }
