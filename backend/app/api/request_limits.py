"""API 层限流辅助：登录、上传与分析入口。"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

from app.api.actor import ActorContext
from app.api.auth_context import client_ip
from app.services.rate_limit import check_rate_limit


def enforce_auth_rate_limit(request: Request) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    ip = client_ip(request) or "unknown"
    if not check_rate_limit(f"auth:{ip}", limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="登录/注册请求过于频繁，请稍后再试。")


def enforce_upload_rate_limit(request: Request, actor: ActorContext) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    if actor.is_guest:
        ip = client_ip(request) or "unknown"
        key = f"upload:guest:{ip}"
        limit = 10
    else:
        key = f"upload:user:{actor.user.id}"
        limit = 30
    if not check_rate_limit(key, limit=limit, window_seconds=60):
        raise HTTPException(status_code=429, detail="上传/分析请求过于频繁，请稍后再试。")
