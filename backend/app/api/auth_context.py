from __future__ import annotations

import secrets
from typing import Any

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.actor import current_user_from_request, guest_session_id_from_request, resolve_actor
from app.api.serializers import user_payload
from app.core.config import settings
from app.core.database import ensure_guest_user
from app.models.entities import AnalysisRecord, AuditLog, User
from app.services.auth import create_session_token
from app.utils.json_tools import dumps


def default_user(db: Session) -> User:
    return ensure_guest_user(db, User)


def current_actor(request: Request, db: Session) -> User:
    return resolve_actor(request, db).user


def require_login(request: Request, db: Session) -> User:
    user = current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(request: Request, db: Session) -> User:
    user = current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_teacher_or_admin(request: Request, db: Session) -> User:
    user = current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    if user.role not in {"admin", "teacher"}:
        raise HTTPException(status_code=403, detail="需要教师或管理员权限")
    return user


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user.id),
        max_age=settings.session_expire_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def auth_response(user: User | None, db: Session, request: Request | None = None) -> dict[str, Any]:
    guest = default_user(db)
    guest_query = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == guest.id)
    if request is not None:
        session_id = guest_session_id_from_request(request)
        if session_id:
            guest_query = guest_query.filter(AnalysisRecord.guest_session_id == session_id)
        else:
            guest_query = guest_query.filter(AnalysisRecord.id < 0)
    guest_history_count = guest_query.count()
    return {
        "authenticated": bool(user),
        "user": user_payload(user) if user else None,
        "mode": "user" if user else "guest",
        "guest_history_count": guest_history_count,
        "wechat": {
            "enabled": False,
            "configured": bool(settings.wechat_app_id and settings.wechat_app_secret and settings.wechat_redirect_uri),
        },
        "platform": {
            "allow_register": settings.allow_register,
            "max_upload_size_mb": settings.max_upload_size_mb,
            "max_zip_total_size_mb": settings.max_zip_total_size_mb,
        },
    }


def write_audit(
    db: Session,
    actor: User,
    request: Request,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    detail: dict[str, Any] | None = None,
    result: str = "success",
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            actor_username=actor.username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_json=dumps(detail or {}),
            ip_address=client_ip(request),
            result=result,
        )
    )


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


def active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.status == "active").count()


def generate_temp_password() -> str:
    return f"Tmp{secrets.token_urlsafe(10)}9!"
