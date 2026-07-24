from pathlib import Path
import json

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)

from app.core.config import get_settings
from app.db import init_db, get_session
from app.knowledge.dynamic_store import DynamicKnowledgeStore
from app.knowledge.graph_service import KnowledgeGraphService as JsonGraphService
from app.knowledge.sync_service import KnowledgeSyncService
from app.langchain.vector_store import DashVectorStore
from app.services.graph_db_service import GraphDBService
from app.pipeline import TripleExtractor

router = APIRouter(prefix="/knowledge", tags=["动态知识库"])


def verify_admin(x_admin_token: str | None = Header(default=None)):
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=403, detail="需要有效管理员 Token（Header: X-Admin-Token）"
        )


def _rebuild_index():
    """重建 DashVector 向量索引（内部函数）。"""
    svc = KnowledgeSyncService()
    docs = svc.load_all_documents()
    store = DashVectorStore()
    store.save(docs)
    from app.api.v1.chat import reload

    reload()


# ==================== MySQL 知识图谱 ====================


@router.get("/graph")
def get_full_graph(entity_type: str | None = None):
    """全量图谱（ECharts 格式）。entity_type 可选筛选: device/component/fault/fault_cause/solution。"""
    try:
        svc = GraphDBService()
        return svc.get_full_graph(entity_type)
    except Exception:
        # MySQL 未连接时回退到 JSON 图谱，转换为 ECharts 兼容格式
        graph = JsonGraphService()._load()
        raw_nodes = graph.get("nodes", [])
        # 旧格式 {id, label, type} → 新格式 {id, name, category}
        # 类型名映射：对齐前端 typeFilter 的 entity_type 值
        TYPE_MAP = {
            "device_model": "device",
            "component": "component",
            "fault": "fault",
            "document": "document",
            "source_file": "source_file",
            "tag": "tag",
        }
        nodes = [
            {"id": n["id"], "name": n.get("label", n.get("id", "")),
             "category": TYPE_MAP.get(n.get("type", "document"), n.get("type", "document"))}
            for n in raw_nodes
        ]
        raw_edges = graph.get("edges", [])
        if entity_type:
            keep_ids = {n["id"] for n in nodes if n["category"] == entity_type}
            nodes = [n for n in nodes if n["category"] == entity_type]
            raw_edges = [e for e in raw_edges
                         if e.get("source") in keep_ids or e.get("target") in keep_ids]
        edges = [
            {"source": e.get("source", ""), "relation": e.get("relation", "关联"),
             "target": e.get("target", "")}
            for e in raw_edges
        ]
        cats = list({n["category"] for n in nodes})
        categories = [
            {"name": c, "itemStyle": {"color": "#4a90d9"}} for c in cats
        ]
        return {
            "code": 200,
            "data": {"nodes": nodes, "edges": edges, "categories": categories},
        }


@router.get("/graph/node/{biz_id}")
def get_node_detail(biz_id: str):
    """单个节点详情 + 邻接关系。"""
    svc = GraphDBService()
    detail = svc.get_node_detail(biz_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"节点 {biz_id} 不存在")
    return {"code": 200, "data": detail}


@router.get("/graph/stats")
def get_graph_stats():
    """各类型实体与关系数量统计。"""
    try:
        svc = GraphDBService()
        return {"code": 200, "data": svc.get_stats()}
    except Exception:
        graph = JsonGraphService()._load()
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        type_counts = {}
        for n in nodes:
            t = n.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        type_counts["relation"] = len(edges)
        return {"code": 200, "data": type_counts, "source": "json_fallback"}


@router.post("/graph/extract", dependencies=[Depends(verify_admin)])
def trigger_extraction():
    """触发全量 LLM 三元组抽取（管理员）。"""
    svc = KnowledgeSyncService()
    docs = svc.load_all_documents()
    extractor = TripleExtractor(batch_size=5)
    result = extractor.extract_from_documents(docs)
    return {
        "code": 200,
        "data": {
            "total_docs": result.total_docs,
            "raw_triples": result.raw_triples,
            "valid_triples": result.valid_triples,
            "unique_triples": result.unique_triples,
            "entities_inserted": result.entities_inserted,
            "relations_inserted": result.relations_inserted,
            "errors": result.errors[:10],
        }
    }


@router.post("/graph/extract/{doc_id}", dependencies=[Depends(verify_admin)])
def trigger_single_extraction(doc_id: str):
    """对指定文档触发 LLM 三元组抽取（管理员）。"""
    svc = KnowledgeSyncService()
    docs = svc.load_all_documents()
    target = [d for d in docs if d.get("id") == doc_id]
    if not target:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    extractor = TripleExtractor(batch_size=1)
    result = extractor.extract_from_documents(target)
    return {
        "code": 200,
        "data": {
            "raw_triples": result.raw_triples,
            "unique_triples": result.unique_triples,
            "entities_inserted": result.entities_inserted,
            "relations_inserted": result.relations_inserted,
        }
    }


# ==================== 旧 JSON 图谱（兼容） ====================


@router.get("/json-graph")
def get_json_graph():
    """JSON 文件图谱（兼容旧接口）。"""
    graph = JsonGraphService()._load()
    return {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])}


@router.get("/devices")
def get_all_devices():
    graph = JsonGraphService()._load()
    devices = []
    for node in graph.get("nodes", []):
        if node.get("type") == "device_model":
            devices.append({"id": node.get("id"), "name": node.get("label")})
    unique_devices = []
    seen_names = set()
    for device in devices:
        if device["name"] not in seen_names:
            seen_names.add(device["name"])
            unique_devices.append(device)
    return sorted(unique_devices, key=lambda x: x["name"])


# ==================== 手册文件管理 ====================


@router.get(
    "/manuals", summary="获取所有手册文件列表", dependencies=[Depends(verify_admin)]
)
def list_manual_files():
    settings = get_settings()
    sync_service = KnowledgeSyncService()
    state = sync_service._load_sync_state()
    file_hashes = state.get("files", {})
    docs = sync_service.load_all_documents()

    doc_count_by_source = {}
    for doc in docs:
        source = doc.get("source", "")
        doc_count_by_source[source] = doc_count_by_source.get(source, 0) + 1

    files = []
    manual_files = sync_service._list_manual_files()
    for p in manual_files:
        size_kb = round(p.stat().st_size / 1024)
        file_type = p.suffix.lower().replace(".", "").upper()
        files.append(
            {
                "filename": p.name,
                "size_kb": size_kb,
                "type": file_type,
                "md5": file_hashes.get(p.name, "未同步"),
                "doc_count": doc_count_by_source.get(p.name, 0),
                "status": "已同步" if p.name in file_hashes else "待同步",
            }
        )
    return sorted(files, key=lambda x: x["filename"])


@router.post(
    "/manuals/upload", summary="上传手册文件", dependencies=[Depends(verify_admin)]
)
async def upload_manual(file: UploadFile = File(...), auto_sync: bool = False):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    save_path = data_dir / file.filename
    content = await file.read()
    save_path.write_bytes(content)
    result = None
    if auto_sync:
        svc = KnowledgeSyncService()
        result = svc.sync()
        _rebuild_index()
    return {
        "success": True,
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 2),
        "auto_sync": auto_sync,
        "sync_result": result,
    }


@router.delete("/manuals/{filename}", dependencies=[Depends(verify_admin)])
def delete_manual(filename: str):
    """删除手册文件及对应知识库文档。"""
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    file_path = data_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件 {filename} 不存在")
    file_path.unlink()
    # 从知识库中移除该文件的所有文档
    svc = KnowledgeSyncService()
    docs = svc.load_all_documents()
    before = len(docs)
    docs = [d for d in docs if d.get("source") != filename]
    after = len(docs)
    svc.knowledge_path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    # 更新同步状态
    state = svc._load_sync_state()
    if filename in state.get("files", {}):
        del state["files"][filename]
        svc._save_sync_state(state)
    return {"success": True, "filename": filename, "removed_docs": before - after}


@router.post("/sync", dependencies=[Depends(verify_admin)])
def trigger_sync():
    """触发全量知识库同步。"""
    svc = KnowledgeSyncService()
    result = svc.sync()
    _rebuild_index()
    return {"success": True, "result": result}


@router.post("/sync/{filename}", dependencies=[Depends(verify_admin)])
def trigger_single_sync(filename: str):
    """单独同步一个手册文件。"""
    settings = get_settings()
    file_path = Path(settings.DATA_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件 {filename} 不存在")
    svc = KnowledgeSyncService()
    try:
        from app.knowledge.document_parser import parse_manual_file, assign_ids
        raw_docs = parse_manual_file(file_path)
        docs = assign_ids(raw_docs, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)[:200]}")
    # 移除旧条目 + 合并新条目
    all_docs = svc.load_all_documents()
    all_docs = [d for d in all_docs if d.get("source") != filename]
    all_docs.extend(docs)
    svc.knowledge_path.write_text(json.dumps(all_docs, ensure_ascii=False, indent=2), encoding="utf-8")
    # 更新同步状态
    state = svc._load_sync_state()
    state["files"][filename] = file_md5(file_path)
    svc._save_sync_state(state)
    _rebuild_index()
    return {"success": True, "filename": filename, "added_docs": len(docs),
            "total_docs": len(all_docs)}


from app.knowledge.document_parser import file_md5

# ==================== 手册上传申请流程 ===


@router.post("/manuals/request", summary="提交手册录入申请")
async def request_manual_upload(
    file: UploadFile = File(...),
    username: str = Form(...),
    description: str = Form(""),
    device_model: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF 和 DOCX 格式")
    settings = get_settings()
    temp_dir = Path(settings.DATA_DIR) / "_pending"
    temp_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    save_path = temp_dir / file.filename
    save_path.write_bytes(content)
    store = DynamicKnowledgeStore()
    req = store.add_manual_request(
        filename=file.filename,
        file_size=len(content),
        applicant=username,
        description=description,
        device_model=device_model,
    )
    return {"success": True, "request": req}


@router.get(
    "/manuals/requests",
    summary="获取手册申请列表",
    dependencies=[Depends(verify_admin)],
)
def list_manual_requests(status: str | None = None):
    store = DynamicKnowledgeStore()
    return {"requests": store.list_manual_requests(status=status)}


@router.post(
    "/manuals/requests/{request_id}/review",
    summary="审核手册申请",
    dependencies=[Depends(verify_admin)],
)
def review_manual_request(
    request_id: str,
    approve: bool = Body(..., embed=True),
    reviewer: str = Body("admin", embed=True),
    comment: str = Body("", embed=True),
    auto_sync: bool = Body(True, embed=True),
):
    store = DynamicKnowledgeStore()
    settings = get_settings()
    temp_dir = Path(settings.DATA_DIR) / "_pending"
    target_dir = Path(settings.DATA_DIR)
    req = store.review_manual_request(
        request_id, approve=approve, reviewer=reviewer, comment=comment
    )
    if approve:
        src = temp_dir / req["filename"]
        dst = target_dir / req["filename"]
        if src.exists():
            import shutil

            shutil.move(str(src), str(dst))
            if auto_sync:
                svc = KnowledgeSyncService()
                result = svc.sync()
                _rebuild_index()
                return {"success": True, "request": req, "sync_result": result}
    return {"success": True, "request": req}
