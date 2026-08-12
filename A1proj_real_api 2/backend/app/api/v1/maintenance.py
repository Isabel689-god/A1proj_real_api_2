"""维修记录 CRUD + CSV 导出 API"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import io
import csv
import threading
from datetime import datetime

from app.db import get_session, MaintenanceRecord

router = APIRouter(prefix="/maintenance", tags=["维修记录"])


class RecordCreate(BaseModel):
    device_model: str = ""
    fault_type: str = ""
    repair_date: str = ""
    technician: str = ""
    description: str = ""
    solution: str = ""
    parts_replaced: str = ""
    status: str = "已完成"
    repair_start_time: Optional[str] = None
    repair_end_time: Optional[str] = None
    repair_duration: str = ""
    fault_cause: str = ""
    fault_resolved: str = "是"
    report_order_id: str = ""


class RecordUpdate(BaseModel):
    device_model: Optional[str] = None
    fault_type: Optional[str] = None
    repair_date: Optional[str] = None
    technician: Optional[str] = None
    description: Optional[str] = None
    solution: Optional[str] = None
    parts_replaced: Optional[str] = None
    status: Optional[str] = None
    repair_start_time: Optional[str] = None
    repair_end_time: Optional[str] = None
    repair_duration: Optional[str] = None
    fault_cause: Optional[str] = None
    fault_resolved: Optional[str] = None


def _safe_datetime(val: str | None):
    """安全解析日期时间，无效时返回 None"""
    if not val or not str(val).strip():
        return None
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _row_to_dict(r: MaintenanceRecord) -> dict:
    return {
        "record_id": r.record_id,
        "user_id": r.user_id,
        "device_model": r.device_model,
        "fault_type": r.fault_type,
        "repair_date": r.repair_date,
        "technician": r.technician,
        "description": r.description,
        "solution": r.solution,
        "parts_replaced": r.parts_replaced,
        "status": r.status,
        "repair_start_time": r.repair_start_time.isoformat() if r.repair_start_time else "",
        "repair_end_time": r.repair_end_time.isoformat() if r.repair_end_time else "",
        "repair_duration": r.repair_duration or "",
        "fault_cause": r.fault_cause or "",
        "fault_resolved": r.fault_resolved or "是",
        "synced": getattr(r, "synced", "未同步") or "未同步",
        "report_order_id": getattr(r, "report_order_id", "") or "",
        "report_submitted": bool(getattr(r, "report_submitted", 0)),
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


@router.get("/records")
def list_records(
    user_id: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
):
    """分页查询维修记录，user_id 为空时返回全部"""
    db = get_session()
    try:
        q = db.query(MaintenanceRecord)
        if user_id:
            q = q.filter(MaintenanceRecord.user_id == user_id)
        q = q.order_by(MaintenanceRecord.updated_at.desc())
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": [_row_to_dict(r) for r in rows],
        }
    finally:
        db.close()


@router.post("/records/{record_id}/sync")
def sync_to_graph(record_id: str, action: str = "sync"):
    """标记维修记录同步/取消同步到知识图谱。

    sync: 标记已同步 + 将记录加入动态知识库(待下次全量同步时索引到向量库)。
    unsync: 仅取消标记。
    """
    db = get_session()
    try:
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.record_id == record_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        if action == "unsync":
            record.synced = "未同步"
        else:
            record.synced = "已同步"
            # 同步时：将维修记录写入动态知识库，下次全量同步时索引到向量库
            try:
                from app.knowledge.dynamic_store import DynamicKnowledgeStore
                store = DynamicKnowledgeStore()
                store.add_case(
                    title=f"{record.device_model or '未知设备'} | {record.fault_type or '未知故障'}",
                    content=(
                        f"设备型号：{record.device_model or '未知'}\n"
                        f"故障类型：{record.fault_type or '未知'}\n"
                        f"故障原因：{record.fault_cause or '未记录'}\n"
                        f"故障描述：{record.description or '未记录'}\n"
                        f"维修方案：{record.solution or '未记录'}\n"
                        f"维修人员：{record.technician or '未记录'}\n"
                        f"是否解决：{record.fault_resolved or '是'}"
                    ),
                    device_model=record.device_model or "",
                    tags=[record.fault_type or "维修"],
                    author="admin",
                )
                # 立即审核通过
                cases = store.list_cases(status="pending")
                for case in cases:
                    if case.get("title") == f"{record.device_model or '未知设备'} | {record.fault_type or '未知故障'}":
                        store.review_case(case["id"], approve=True, reviewer="system")
                        break
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"维修记录写入动态知识库失败: {e}")

        db.commit()
        return {"success": True, "synced": record.synced}
    finally:
        db.close()


@router.post("/records")
def create_record(req: RecordCreate, user_id: str = Query(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """新增维修记录"""
    db = get_session()
    try:
        record = MaintenanceRecord(
            record_id=f"mr:{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            device_model=req.device_model,
            fault_type=req.fault_type,
            repair_date=req.repair_date,
            technician=req.technician,
            description=req.description,
            solution=req.solution,
            parts_replaced=req.parts_replaced,
            status=req.status,
            repair_start_time=_safe_datetime(req.repair_start_time),
            repair_end_time=_safe_datetime(req.repair_end_time),
            repair_duration=req.repair_duration,
            fault_cause=req.fault_cause,
            fault_resolved=req.fault_resolved,
            report_order_id=req.report_order_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        # 后台自动同步到案例库
        background_tasks.add_task(_auto_sync_by_id, record.record_id)
        return {"success": True, "record": _row_to_dict(record)}
    finally:
        db.close()


@router.put("/records/{record_id}")
def update_record(record_id: str, req: RecordUpdate, user_id: str = Query(""), background_tasks: BackgroundTasks = BackgroundTasks()):
    """修改维修记录（不传 user_id 时管理员可修改任意记录）"""
    db = get_session()
    try:
        q = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id)
        if user_id:
            q = q.filter(MaintenanceRecord.user_id == user_id)
        record = q.first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        for field, value in req.dict(exclude_unset=True).items():
            setattr(record, field, value)
        db.commit()
        db.refresh(record)
        # 后台自动同步到案例库
        background_tasks.add_task(_auto_sync_by_id, record.record_id)
        return {"success": True, "record": _row_to_dict(record)}
    finally:
        db.close()


@router.delete("/records/{record_id}")
def delete_record(record_id: str, user_id: str = Query("")):
    """删除维修记录（不传 user_id 时管理员可删除任意记录）"""
    db = get_session()
    try:
        q = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id)
        if user_id:
            q = q.filter(MaintenanceRecord.user_id == user_id)
        record = q.first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        db.delete(record)
        db.commit()
        return {"success": True}
    finally:
        db.close()


@router.get("/records/export")
def export_records(user_id: str = Query("")):
    """导出维修记录为 CSV，user_id 为空时导出全部"""
    db = get_session()
    try:
        q = db.query(MaintenanceRecord)
        if user_id:
            q = q.filter(MaintenanceRecord.user_id == user_id)
        rows = q.order_by(MaintenanceRecord.created_at.desc()).all()

        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM for Excel
        writer = csv.writer(output)
        writer.writerow([
            "记录编号", "设备型号", "故障类型", "维修日期", "维修人员",
            "故障描述", "维修方案", "更换配件", "状态",
            "维修开始时间", "维修结束时间", "维修用时",
            "故障原因分析", "是否解决故障",
            "创建时间", "更新时间"
        ])
        for r in rows:
            writer.writerow([
                r.record_id, r.device_model, r.fault_type, r.repair_date,
                r.technician, r.description, r.solution, r.parts_replaced,
                r.status,
                r.repair_start_time.isoformat() if r.repair_start_time else "",
                r.repair_end_time.isoformat() if r.repair_end_time else "",
                r.repair_duration or "",
                r.fault_cause or "",
                r.fault_resolved or "",
                r.created_at.isoformat() if r.created_at else "",
                r.updated_at.isoformat() if r.updated_at else "",
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=maintenance_records_{datetime.now().strftime('%Y%m%d')}.csv"
            },
        )
    finally:
        db.close()


@router.get("/reports/sync")
def get_synced_reports(user_id: str = Query(...)):
    """获取用户持久化报告。"""
    db = get_session()
    try:
        records = (
            db.query(MaintenanceRecord)
            .filter(
                MaintenanceRecord.user_id == user_id,
                MaintenanceRecord.report_data.isnot(None),
            )
            .order_by(MaintenanceRecord.created_at.desc())
            .limit(200)
            .all()
        )
        result = []
        for r in records:
            if r.report_data:
                result.append(r.report_data)
        return {"reports": result}
    finally:
        db.close()


@router.post("/reports/sync")
def save_report(req: dict, user_id: str = Query(...)):
    """保存完整维修报告到 MySQL。"""
    order_id = req.get("orderId", "")
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少 orderId")

    db = get_session()
    try:
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.report_order_id == order_id
        ).first()
        if record:
            record.report_data = req
            record.report_submitted = 1 if req.get("submitStatus") == "已提交" else 0
        else:
            record = MaintenanceRecord(
                record_id=f"mr:{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                report_order_id=order_id,
                report_data=req,
                report_submitted=1 if req.get("submitStatus") == "已提交" else 0,
                status="已提交" if req.get("submitStatus") == "已提交" else "已创建",
            )
            db.add(record)
        db.commit()
        return {"success": True}
    finally:
        db.close()


@router.post("/records/submit-report")
def submit_report(req: dict, user_id: str = Query("system")):
    """保存提报状态"""
    db = get_session()
    try:
        order_id = req.get("report_order_id", "")
        if not order_id:
            raise HTTPException(status_code=400, detail="缺少 report_order_id")
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.report_order_id == order_id
        ).first()
        if record:
            record.report_submitted = 1
            db.commit()
        else:
            record = MaintenanceRecord(
                record_id=f"mr:{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                report_order_id=order_id,
                report_submitted=1,
            )
            db.add(record)
            db.commit()
        return {"success": True, "record_id": record.record_id}
    finally:
        db.close()


@router.get("/records/check-submitted/{order_id}")
def check_submitted(order_id: str):
    """查询工单是否已提交"""
    db = get_session()
    try:
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.report_order_id == order_id,
            MaintenanceRecord.report_submitted == 1,
        ).first()
        return {"submitted": record is not None}
    finally:
        db.close()


def _auto_sync_by_id(record_id: str):
    """后台任务：按 ID 查询记录并自动同步。"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"auto_sync 后台任务启动: {record_id}")
        db = get_session()
        record = db.query(MaintenanceRecord).filter(MaintenanceRecord.record_id == record_id).first()
        db.close()
        if record:
            from app.services.auto_sync import auto_sync_to_case_library
            auto_sync_to_case_library(record)
            logger.info(f"auto_sync 后台任务完成: {record_id}")
        else:
            logger.warning(f"auto_sync 未找到记录: {record_id}")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"auto_sync 后台任务异常: {e}")
