"""从知识条目构建维修知识图谱（设备-部件-故障-文档关系）。"""
from __future__ import annotations

import re
from typing import Any

FAULT_PATTERNS = [
    r"故障", r"报警", r"失效", r"异常", r"损坏", r"错误",
]
MAX_TAG_EDGES_PER_DOC = 1
MAX_FAULT_EDGES_PER_DOC = 1
MAX_COMPONENT_EDGES_PER_DOC = 1
MAX_DOCS = 350

COMPONENT_WORDS = [
    "屏幕", "电池", "摄像头", "主板", "伺服", "主轴", "进给", "数控系统",
    "编码器", "驱动器", "电源",
]


def _nid(kind: str, label: str) -> str:
    slug = re.sub(r"\s+", "_", label.strip())[:60]
    return f"{kind}:{slug}"


def build_graph_from_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if len(documents) > MAX_DOCS:
        step = len(documents) / MAX_DOCS
        documents = [documents[int(i * step)] for i in range(MAX_DOCS)]

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(nid: str, label: str, ntype: str, **extra):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": label, "type": ntype, **extra}

    def add_edge(src: str, rel: str, dst: str):
        key = (src, rel, dst)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": src, "target": dst, "relation": rel})

    for doc in documents:
        doc_id = doc.get("id", "")
        title = doc.get("title", "未命名")
        source = doc.get("source", "")
        dn = _nid("doc", doc_id)
        add_node(dn, title, "document", source=source)

        # 源文件 & 设备节点（无连边，仅作维度标注）
        add_node(_nid("file", source), source, "source_file")
        from pathlib import Path as _Path
        device = _Path(source).stem if source else title.split("｜")[0][:40]
        add_node(_nid("device", device), device, "device_model")
        add_edge(_nid("device", device), "包含文档", dn)

        text = f"{title} {doc.get('content', '')}"

        tag_count = 0
        for tag in doc.get("tags", []):
            if tag_count >= MAX_TAG_EDGES_PER_DOC:
                break
            tn = _nid("tag", tag)
            add_node(tn, tag, "tag")
            add_edge(dn, "标注", tn)
            tag_count += 1

        # 部件边：每文档最多 1 条
        comp_count = 0
        for word in COMPONENT_WORDS:
            if comp_count >= MAX_COMPONENT_EDGES_PER_DOC:
                break
            if word in text:
                cn = _nid("component", word)
                add_node(cn, word, "component")
                add_edge(dn, "涉及部件", cn)
                comp_count += 1

        seen_faults: set[str] = set()
        for pat in FAULT_PATTERNS:
            if len(seen_faults) >= MAX_FAULT_EDGES_PER_DOC:
                break
            for m in re.finditer(pat, text):
                if len(seen_faults) >= MAX_FAULT_EDGES_PER_DOC:
                    break
                fault = m.group(0)
                if fault not in seen_faults:
                    seen_faults.add(fault)
                    fn = _nid("fault", fault)
                    add_node(fn, fault, "fault")
                    add_edge(dn, "描述故障", fn)

    return {"nodes": list(nodes.values()), "edges": edges}
