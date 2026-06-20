from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.platform import (
    active_admin_count,
    build_admin_stats,
    delete_record_with_files,
    generate_temp_password,
    list_admin_audit_logs,
    list_admin_records,
    list_admin_users,
    require_admin,
    user_payload,
    write_audit,
)
from app.api.schemas import AdminAiConfigRequest, ResetPasswordRequest, UserRoleRequest, UserStatusRequest
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import AnalysisRecord, JobProfile, User
from app.services.auth import hash_password, validate_password_strength
from app.services.runtime_config import get_ai_runtime_config, update_ai_runtime_config

router = APIRouter()


@router.get("/admin/jobs")
def admin_job_profiles(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    require_admin(request, db)
    rows = db.query(JobProfile, User).join(User, JobProfile.user_id == User.id).order_by(JobProfile.updated_at.desc()).limit(200).all()
    return [
        {
            "id": profile.id,
            "name": profile.name,
            "category": profile.category,
            "target_position": profile.target_position,
            "status": profile.status,
            "owner": profile.user_id,
            "owner_name": user.display_name or user.username,
            "username": user.username,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
        }
        for profile, user in rows
    ]


@router.get("/admin/stats")
def admin_stats(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    return build_admin_stats(admin, db)


@router.get("/admin/users")
def admin_users(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    require_admin(request, db)
    return list_admin_users(db)


@router.patch("/admin/users/{user_id}/status")
def admin_update_user_status(user_id: int, payload: UserStatusRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    if payload.status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="账号状态只能是 active 或 disabled")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == settings.default_user_name:
        raise HTTPException(status_code=400, detail="不能禁用游客账号")
    if user.id == admin.id and payload.status == "disabled":
        raise HTTPException(status_code=400, detail="不能禁用当前管理员账号")
    if user.role == "admin" and payload.status == "disabled" and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="不能禁用最后一个管理员")
    user.status = payload.status
    write_audit(db, admin, request, "admin.user.status", "user", user.id, {"status": payload.status})
    db.commit()
    db.refresh(user)
    return {"updated": True, "user": user_payload(user)}


@router.patch("/admin/users/{user_id}/role")
def admin_update_user_role(user_id: int, payload: UserRoleRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    role = payload.role.strip().lower()
    if role not in {"user", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="角色只能是 user、teacher 或 admin")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == settings.default_user_name:
        raise HTTPException(status_code=400, detail="不能修改游客账号角色")
    if user.id == admin.id and role != "admin":
        raise HTTPException(status_code=400, detail="不能修改当前管理员自己的角色")
    if user.role == "admin" and role != "admin" and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="不能降级最后一个管理员")
    if user.role == role:
        return {"updated": True, "user": user_payload(user)}
    previous_role = user.role
    user.role = role
    write_audit(db, admin, request, "admin.user.role", "user", user.id, {"from": previous_role, "to": role})
    db.commit()
    db.refresh(user)
    return {"updated": True, "user": user_payload(user)}


@router.post("/admin/users/{user_id}/reset-password")
def admin_reset_user_password(user_id: int, payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == settings.default_user_name:
        raise HTTPException(status_code=400, detail="游客账号没有密码")
    next_password = payload.password or generate_temp_password()
    validate_password_strength(next_password, payload.confirm_password or next_password)
    user.password_hash = hash_password(next_password)
    write_audit(db, admin, request, "admin.user.reset_password", "user", user.id, {"generated": not bool(payload.password)})
    db.commit()
    return {"updated": True, "user_id": user.id, "temporary_password": next_password if not payload.password else ""}


@router.get("/admin/records")
def admin_records(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    require_admin(request, db)
    return list_admin_records(db)


@router.delete("/admin/records/{record_id}")
def admin_delete_record(record_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    try:
        deleted_id = delete_record_with_files(db, record)
        write_audit(db, admin, request, "admin.record.delete", "analysis_record", deleted_id, {"filename": record.original_filename})
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="无法删除该用户记录，请稍后再试。") from exc
    return {"deleted": True, "record_id": deleted_id}


@router.get("/admin/audit-logs")
def admin_audit_logs(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    require_admin(request, db)
    return list_admin_audit_logs(db)


@router.get("/admin/ai-config")
def admin_ai_config(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    require_admin(request, db)
    config = get_ai_runtime_config()
    return {
        "provider": config["provider"],
        "api_url": config["api_url"],
        "model": config["model"],
        "api_key_configured": config["api_key_configured"],
        "api_key_masked": config["api_key_masked"],
        "using_local_override": config["using_local_override"],
        "provider_options": [
            {"value": "deepseek", "label": "DeepSeek"},
            {"value": "openai_compatible", "label": "OpenAI Compatible"},
        ],
        "model_suggestions": [
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4.1-mini",
            "gpt-4o-mini",
            "glm-4-flash",
            "qwen-plus",
        ],
    }


@router.put("/admin/ai-config")
def admin_update_ai_config(payload: AdminAiConfigRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    admin = require_admin(request, db)
    try:
        config = update_ai_runtime_config(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_audit(
        db,
        admin,
        request,
        "admin.ai_config.update",
        "system",
        None,
        {
            "provider": config["provider"],
            "model": config["model"],
            "api_url": config["api_url"],
            "api_key_changed": bool(payload.api_key) or payload.clear_api_key,
        },
    )
    db.commit()
    return {
        "saved": True,
        "provider": config["provider"],
        "api_url": config["api_url"],
        "model": config["model"],
        "api_key_configured": config["api_key_configured"],
        "api_key_masked": config["api_key_masked"],
        "using_local_override": config["using_local_override"],
    }
