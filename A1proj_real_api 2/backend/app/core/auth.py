"""JWT 鉴权：签发、验证、FastAPI 依赖。"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

# ── 配置 ──────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_EXPIRE_HOURS = 24  # 普通用户 token 有效期
ADMIN_EXPIRE_HOURS = 12   # 管理员 token 有效期

security = HTTPBearer(auto_error=False)


def _secret() -> str:
    """从配置取 JWT 密钥，无配置时用机器唯一指纹兜底。"""
    settings = get_settings()
    configured = getattr(settings, "JWT_SECRET", "") or ""
    if configured:
        return configured
    # 兜底：基于 hostname + cwd 生成稳定密钥
    import os
    fingerprint = f"{os.uname().nodename}:{os.getcwd()}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def _hash_password(password: str) -> str:
    """SHA-256 哈希密码（轻量替代 passlib）。"""
    salt = _secret()[:16]
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return _hash_password(password) == stored_hash


def create_token(user_id: str, group: str, permissions: list[str], is_admin: bool = False) -> str:
    """签发 JWT。"""
    expire_hours = ADMIN_EXPIRE_HOURS if is_admin else ACCESS_EXPIRE_HOURS
    payload: dict[str, Any] = {
        "sub": user_id,
        "group": group,
        "permissions": permissions,
        "is_admin": is_admin,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expire_hours),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """验证并解码 JWT。异常时抛 HTTPException。"""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")


# ── FastAPI 依赖 ──────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """从请求头或 cookie 提取并验证 JWT，返回 payload。"""
    # 1. Authorization header
    if credentials:
        return decode_token(credentials.credentials)
    # 2. Cookie
    cookie_token = request.cookies.get("a1proj_token")
    if cookie_token:
        return decode_token(cookie_token)
    # 3. Query param（WebSocket 等场景）
    token = request.query_params.get("token")
    if token:
        return decode_token(token)
    raise HTTPException(status_code=401, detail="请先登录")


def verify_admin(request: Request) -> dict[str, Any]:
    """管理员鉴权：优先 JWT (header/cookie/query)，回退 X-Admin-Token。"""
    token = None
    # 1. Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    # 2. Cookie
    if not token:
        token = request.cookies.get("a1proj_token")
    # 3. Query param
    if not token:
        token = request.query_params.get("token")

    if token:
        payload = decode_token(token)
        if payload.get("is_admin"):
            return payload
        raise HTTPException(status_code=403, detail="需要管理员权限")

    # 回退：兼容旧的 X-Admin-Token
    legacy_token = request.headers.get("X-Admin-Token", "")
    settings = get_settings()
    configured = getattr(settings, "ADMIN_TOKEN", "admin-change-me")
    if legacy_token and legacy_token == configured:
        return {"sub": "admin", "group": "管理人员", "is_admin": True}
    raise HTTPException(status_code=401, detail="请先以管理员身份登录")


def hash_password(password: str) -> str:
    """对外暴露的密码哈希（注册/修改密码时用）。"""
    return _hash_password(password)
