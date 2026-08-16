from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models.entities import AnalysisRecord, AuditLog, JobProfile, User
from app.utils.json_tools import loads


def user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "role": user.role,
        "status": user.status,
    }


def admin_user_payload(user: User, record_count: int = 0, batch_count: int = 0) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else "",
        "record_count": int(record_count or 0),
        "batch_count": int(batch_count or 0),
    }


def admin_record_payload(record: AnalysisRecord, user: User) -> dict[str, Any]:
    job_profile_name = getattr(record, "_job_profile_name", "")
    sections = loads(record.sections_json, {})
    if not isinstance(sections, dict):
        sections = {}
    return {
        "record_id": record.id,
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "filename": record.original_filename,
        "target_position": record.target_position,
        "job_profile_name": job_profile_name,
        "total_score": record.total_score,
        "analysis_mode": record.analysis_mode,
        "analysis_mode_label": public_analysis_mode_label(record.analysis_mode, sections),
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def audit_log_payload(log: AuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "actor_username": log.actor_username,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "detail": loads(log.detail_json, {}),
        "ip_address": log.ip_address,
        "result": log.result,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    }


def normalize_job_profile_payload(payload: Any) -> dict[str, str]:
    name = payload.name.strip()[:120]
    if not name:
        raise HTTPException(status_code=400, detail="岗位模板名称不能为空。")
    status = payload.status if payload.status in {"active", "draft", "archived"} else "active"
    return {
        "name": name,
        "category": payload.category.strip()[:100],
        "target_position": payload.target_position.strip()[:120],
        "description": payload.description.strip(),
        "requirement_summary": payload.requirement_summary.strip(),
        "status": status,
    }


def job_profile_payload(profile: JobProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "category": profile.category,
        "target_position": profile.target_position,
        "description": profile.description,
        "requirement_summary": profile.requirement_summary,
        "status": profile.status,
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


def mode_label(mode: str) -> str:
    labels = {
        "ai_first": "规则分析",
        "core": "规则分析",
        "deepseek": "增强分析已完成",
        "offline_fallback": "规则分析",
        "offline": "规则分析",
    }
    return labels.get(mode, mode)


def public_analysis_mode_label(
    mode: str,
    sections: dict[str, Any] | None = None,
    *,
    ai_requested: bool | None = None,
    ai_enhancement_status: str | None = None,
) -> str:
    sections = sections if isinstance(sections, dict) else {}
    requested = bool(sections.get("_ai_requested")) if ai_requested is None else bool(ai_requested)
    status = str(sections.get("_ai_enhancement_status") or ai_enhancement_status or "")
    if requested:
        if mode == "deepseek" or status == "success":
            return "增强分析已完成"
        if status in {"pending", "processing"}:
            return "增强分析进行中"
        return mode_label(mode)
    return mode_label(mode)


def batch_status_label(status: str) -> str:
    labels = {
        "pending": "等待处理",
        "processing": "正在分析",
        "paused": "已暂停",
        "success": "已完成",
        "partial_success": "部分完成",
        "failed": "处理失败",
    }
    return labels.get(status, status)


def task_type_label(task_type: str) -> str:
    labels = {
        "batch_analysis": "批量分析",
        "single_analysis": "单份分析",
    }
    return labels.get(task_type, task_type or "分析任务")

