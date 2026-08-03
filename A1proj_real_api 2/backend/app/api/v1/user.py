from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional

from app.services.user_service import user_service
from app.services.group_service import group_service
from app.api.v1.knowledge import verify_admin

router = APIRouter(prefix="/user", tags=["用户管理"])

class LoginRequest(BaseModel):
    username: str
    password: str

class AddUserRequest(BaseModel):
    username: str
    password: str
    group: str

class UpdateGroupRequest(BaseModel):
    group: str

@router.post("/login")
def login(req: LoginRequest):
    user = user_service.login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"success": True, "user": user}

@router.post("/logout")
def logout(username: str = Body(..., embed=True)):
    user_service.logout(username)
    return {"success": True}

@router.get("/list", dependencies=[Depends(verify_admin)])
def list_users():
    return {"users": user_service.get_all_users()}

@router.post("/add", dependencies=[Depends(verify_admin)])
def add_user(req: AddUserRequest):
    success = user_service.add_user(req.username, req.password, req.group)
    if not success:
        raise HTTPException(status_code=400, detail="用户已存在或权限组不合法")
    return {"success": True}

@router.put("/{username}/group", dependencies=[Depends(verify_admin)])
def update_user_group(username: str, req: UpdateGroupRequest):
    success = user_service.update_user_group(username, req.group)
    if not success:
        raise HTTPException(status_code=400, detail="用户不存在或权限组不合法")
    return {"success": True}

@router.delete("/{username}", dependencies=[Depends(verify_admin)])
def delete_user(username: str):
    success = user_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=400, detail="无法删除该用户")
    return {"success": True}

class UpdatePermsRequest(BaseModel):
    extra_permissions: List[str]

@router.put("/{username}/permissions", dependencies=[Depends(verify_admin)])
def update_user_permissions(username: str, req: UpdatePermsRequest):
    success = user_service.update_user_permissions(username, req.extra_permissions)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True}


# ═══════════ 权限组管理 ═══════════

class GroupCreateRequest(BaseModel):
    name: str
    description: str = ""
    permissions: List[str] = []


class GroupEditRequest(BaseModel):
    description: str = ""
    permissions: List[str] = []


@router.get("/groups", dependencies=[Depends(verify_admin)])
def list_groups():
    groups = group_service.list_groups()
    # 从用户数据动态注入成员列表
    all_users = user_service.get_all_users()
    for name in groups:
        groups[name]["members"] = [u["username"] for u in all_users if u["group"] == name]
    return {"groups": groups}


@router.post("/groups", dependencies=[Depends(verify_admin)])
def create_group(req: GroupCreateRequest):
    ok = group_service.create_group(req.name, req.description, req.permissions)
    if not ok:
        raise HTTPException(status_code=400, detail="权限组已存在")
    return {"success": True}


@router.put("/groups/{name}", dependencies=[Depends(verify_admin)])
def update_group(name: str, req: GroupEditRequest):
    ok = group_service.update_group(name, req.description, req.permissions)
    if not ok:
        raise HTTPException(status_code=404, detail="权限组不存在")
    return {"success": True}


@router.delete("/groups/{name}", dependencies=[Depends(verify_admin)])
def delete_group(name: str):
    ok = group_service.delete_group(name)
    if not ok:
        raise HTTPException(status_code=404, detail="权限组不存在")
    return {"success": True}
