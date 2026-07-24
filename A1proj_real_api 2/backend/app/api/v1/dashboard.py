"""故障统计看板 API —— 数字大屏数据源。"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from fastapi import APIRouter

from app.core.config import get_settings
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.sync_service import KnowledgeSyncService

router = APIRouter(prefix="/dashboard", tags=["数字大屏"])


@router.get("/overview")
def get_overview():
    """全量统计数据，驱动数字大屏。"""
    settings = get_settings()

    # ── JSON 图谱（始终可用）──
    graph_svc = KnowledgeGraphService()
    graph = graph_svc._load()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_by_type = defaultdict(list)
    for n in nodes:
        node_by_type[n.get("type", "unknown")].append(n)

    # ── 知识库文档 ──
    sync_svc = KnowledgeSyncService()
    docs = sync_svc.load_all_documents()

    # ── MySQL 图谱（优先，数据更丰富）──
    mysql_ok = False
    try:
        from app.services.graph_db_service import GraphDBService
        mysql = GraphDBService()
        mysql_stats = mysql.get_stats()
        mysql_device_fault = _mysql_device_fault_links(mysql)
        mysql_ok = True
    except Exception:
        mysql_stats = {}
        mysql_device_fault = []

    # ═══════════════════════════════════════
    # 1. 概览卡片（优先 MySQL）
    # ═══════════════════════════════════════
    overview = {
        "total_devices": mysql_stats.get("device", len(node_by_type.get("device_model", []))),
        "total_components": mysql_stats.get("component", len(node_by_type.get("component", []))),
        "total_faults": mysql_stats.get("fault", len(node_by_type.get("fault", []))),
        "total_documents": len(docs),
        "total_causes": mysql_stats.get("fault_cause", 0),
        "total_solutions": mysql_stats.get("solution", 0),
        "total_relations": mysql_stats.get("relation", len(edges)),
    }

    # ═══════════════════════════════════════
    # 2. 各设备型号故障关联数
    # ═══════════════════════════════════════
    if mysql_device_fault:
        device_fault_links = mysql_device_fault
    else:
        device_fault_links = _json_device_fault_links(nodes, edges)

    # ═══════════════════════════════════════
    # 3. 故障原因分布
    # ═══════════════════════════════════════
    fault_cause_dist = _mysql_fault_cause_dist() if mysql_ok else []

    # ═══════════════════════════════════════
    # 4. 文档来源分布
    # ═══════════════════════════════════════
    source_counter = Counter(d.get("source", "unknown") for d in docs)
    source_dist = [
        {"name": k, "value": v} for k, v in source_counter.most_common(8)
    ]

    # ═══════════════════════════════════════
    # 5. 标签热力（top 12）
    # ═══════════════════════════════════════
    tag_counter = Counter()
    for d in docs:
        raw = d.get("tags", "[]")
        try:
            tags = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            tags = []
        for t in tags:
            tag_counter[t.strip()] += 1
    tag_dist = [
        {"name": k, "value": v} for k, v in tag_counter.most_common(12)
    ]

    # ═══════════════════════════════════════
    # 6. 解决方案风险等级分布
    # ═══════════════════════════════════════
    risk_dist = _mysql_risk_dist() if mysql_ok else []

    # ═══════════════════════════════════════
    # 7. 实体关系网络概览
    # ═══════════════════════════════════════
    entity_summary = [
        {"name": "设备型号", "value": overview["total_devices"]},
        {"name": "部件", "value": overview["total_components"]},
        {"name": "故障", "value": overview["total_faults"]},
        {"name": "故障原因", "value": overview["total_causes"]},
        {"name": "解决方案", "value": overview["total_solutions"]},
    ]

    return {
        "code": 200,
        "data": {
            "overview": overview,
            "entity_summary": entity_summary,
            "device_fault_links": device_fault_links,
            "fault_cause_distribution": fault_cause_dist,
            "source_distribution": source_dist,
            "tag_distribution": tag_dist,
            "risk_distribution": risk_dist,
        }
    }


# ═══════════════════════════════════════
# MySQL 查询辅助
# ═══════════════════════════════════════

def _mysql_device_fault_links(mysql) -> list[dict]:
    """MySQL: 每个设备型号通过关系关联到多少故障。"""
    from app.db import get_session
    from sqlalchemy import text
    session = get_session()
    try:
        rows = session.execute(text(
            "SELECT d.name, COUNT(DISTINCT r.dst_id) AS cnt "
            "FROM device d "
            "JOIN relation r ON r.src_id = d.biz_id AND r.dst_type = 'fault' "
            "GROUP BY d.name ORDER BY cnt DESC LIMIT 10"
        )).fetchall()
        return [{"name": r[0], "value": r[1]} for r in rows]
    except Exception:
        return []
    finally:
        session.close()


def _mysql_fault_cause_dist() -> list[dict]:
    from app.db import get_session
    from sqlalchemy import text
    session = get_session()
    try:
        rows = session.execute(text(
            "SELECT f.name, COUNT(r.id) AS cnt "
            "FROM fault f "
            "JOIN relation r ON r.src_id = f.biz_id AND r.dst_type = 'fault_cause' "
            "GROUP BY f.name ORDER BY cnt DESC LIMIT 10"
        )).fetchall()
        return [{"name": r[0], "value": r[1]} for r in rows]
    except Exception:
        return []
    finally:
        session.close()


def _mysql_risk_dist() -> list[dict]:
    from app.db import get_session
    from sqlalchemy import text
    session = get_session()
    try:
        rows = session.execute(text(
            "SELECT risk_level, COUNT(*) AS cnt FROM solution GROUP BY risk_level"
        )).fetchall()
        return [{"name": r[0], "value": r[1]} for r in rows]
    except Exception:
        return []
    finally:
        session.close()


def _json_device_fault_links(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """JSON 图谱回退：统计每个设备关联的故障数。"""
    node_map = {n["id"]: n for n in nodes}
    device_ids = {n["id"] for n in nodes if n.get("type") == "device_model"}
    fault_ids = {n["id"] for n in nodes if n.get("type") == "fault"}
    device_fault_count = defaultdict(set)

    for edge in edges:
        src, dst = edge.get("source", ""), edge.get("target", "")
        if src in device_ids and dst in fault_ids:
            device_fault_count[src].add(dst)
        elif dst in device_ids and src in fault_ids:
            device_fault_count[dst].add(src)
        # 间接: device→component→fault
        if src in device_ids and node_map.get(dst, {}).get("type") == "component":
            for e2 in edges:
                if e2.get("source") == dst and e2.get("target") in fault_ids:
                    device_fault_count[src].add(e2.get("target"))
                elif e2.get("target") == dst and e2.get("source") in fault_ids:
                    device_fault_count[src].add(e2.get("source"))

    result = []
    for n in nodes:
        if n.get("type") == "device_model":
            result.append({
                "name": n.get("label", n.get("id", "")),
                "value": len(device_fault_count.get(n["id"], set())),
            })
    result.sort(key=lambda x: x["value"], reverse=True)
    return result
