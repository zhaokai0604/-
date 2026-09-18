from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.platform import auth_response, import_guest_records, set_session_cookie
from app.api.request_limits import enforce_auth_rate_limit
from app.api.schemas import LoginRequest, RegisterRequest
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import AuditLog, User
from app.services.auth import (
    hash_password,
    normalize_username,
    password_strength,
    validate_password_strength,
    validate_username,
    verify_password,
)

router = APIRouter()


def _enforce_auth_rate_limit(request: Request) -> None:
    enforce_auth_rate_limit(request)


@router.post("/auth/register")
def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    from fastapi import HTTPException

    _enforce_auth_rate_limit(request)
    if not settings.allow_register:
        raise HTTPException(status_code=403, detail="当前系统未开放注册")
    username = validate_username(payload.username)
    validate_password_strength(payload.password, payload.confirm_password)
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="用户名已存在")
    display_name = payload.display_name.strip()[:100] or username
    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(payload.password),
        role="user",
        status="active",
        organization_id=settings.default_organization_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user)
    data = auth_response(user, db, request)
    data["password_strength"] = password_strength(payload.password)
    return data


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    from fastapi import HTTPException

    from app.api.platform import client_ip
    from app.utils.time import utc_now

    _enforce_auth_rate_limit(request)
    username = normalize_username(payload.username)
    user = db.query(User).filter(User.username == username).first()
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user.last_login_at = utc_now()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            actor_username=user.username,
            action="auth.login",
            target_type="user",
            target_id=user.id,
            detail_json='{"mode":"password"}',
            ip_address=client_ip(request),
            result="success",
        )
    )
    db.commit()
    set_session_cookie(response, user)
    return auth_response(user, db, request)


@router.post("/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    from app.api.platform import clear_session_cookie

    clear_session_cookie(response)
    return {"logged_out": True}


@router.get("/auth/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.platform import current_user_from_request

    return auth_response(current_user_from_request(request, db), db, request)


@router.post("/auth/import-guest-history")
def import_guest_history(request: Request, db: Session = Depends(get_db)) -> dict[str, int]:
    return import_guest_records(request, db)
