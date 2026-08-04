"""维修记录 CRUD + CSV 导出 API"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import io
import csv
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


class RecordUpdate(BaseModel):
    device_model: Optional[str] = None
    fault_type: Optional[str] = None
    repair_date: Optional[str] = None
    technician: Optional[str] = None
    description: Optional[str] = None
    solution: Optional[str] = None
    parts_replaced: Optional[str] = None
    status: Optional[str] = None


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
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


@router.get("/records")
def list_records(
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页查询当前用户的维修记录"""
    db = get_session()
    try:
        q = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.user_id == user_id
        ).order_by(MaintenanceRecord.updated_at.desc())
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


@router.post("/records")
def create_record(req: RecordCreate, user_id: str = Query(...)):
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
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"success": True, "record": _row_to_dict(record)}
    finally:
        db.close()


@router.put("/records/{record_id}")
def update_record(record_id: str, req: RecordUpdate, user_id: str = Query(...)):
    """修改维修记录（仅允许修改自己的记录）"""
    db = get_session()
    try:
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.record_id == record_id,
            MaintenanceRecord.user_id == user_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        for field, value in req.dict(exclude_unset=True).items():
            setattr(record, field, value)
        db.commit()
        db.refresh(record)
        return {"success": True, "record": _row_to_dict(record)}
    finally:
        db.close()


@router.delete("/records/{record_id}")
def delete_record(record_id: str, user_id: str = Query(...)):
    """删除维修记录"""
    db = get_session()
    try:
        record = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.record_id == record_id,
            MaintenanceRecord.user_id == user_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        db.delete(record)
        db.commit()
        return {"success": True}
    finally:
        db.close()


@router.get("/records/export")
def export_records(user_id: str = Query(...)):
    """导出当前用户全部维修记录为 CSV"""
    db = get_session()
    try:
        rows = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.user_id == user_id
        ).order_by(MaintenanceRecord.created_at.desc()).all()

        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM for Excel
        writer = csv.writer(output)
        writer.writerow([
            "记录编号", "设备型号", "故障类型", "维修日期", "维修人员",
            "故障描述", "维修方案", "更换配件", "状态", "创建时间", "更新时间"
        ])
        for r in rows:
            writer.writerow([
                r.record_id, r.device_model, r.fault_type, r.repair_date,
                r.technician, r.description, r.solution, r.parts_replaced,
                r.status,
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
