from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import secrets
import shutil
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, ensure_guest_user
from app.api.actor import (
    ActorContext,
    actor_guest_session_value,
    batch_owned_by_actor,
    current_user_from_request,
    guest_session_id_from_request,
    record_owned_by_actor,
    resolve_actor,
    scope_batches,
    scope_job_profiles,
    scope_records,
)
from app.models.entities import AnalysisRecord, AuditLog, BatchTask, JobProfile, Report, UploadedFile, User
from app.services.ai import enhance_with_deepseek
from app.services.auth import create_session_token, hash_password, password_strength, validate_password_strength, verify_password
from app.services.document_ingest import ingest_resume
from app.services.report import generate_reports
from app.services.scoring import analyze_resume
from app.services.storage import remove_path
from app.services.zip_service import safe_extract_zip
from app.utils.json_tools import dumps, loads


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
        "analysis_mode_label": mode_label(record.analysis_mode),
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


def resolve_job_profile(db: Session, actor: ActorContext, job_profile_id: int) -> JobProfile | None:
    if not job_profile_id or job_profile_id <= 0:
        return None
    profile = scope_job_profiles(db.query(JobProfile), actor).filter(JobProfile.id == job_profile_id, JobProfile.status != "archived").first()
    if not profile:
        raise HTTPException(status_code=404, detail="所选岗位模板不存在。")
    return profile


def resolve_job_inputs(target_position: str, job_description: str, profile: JobProfile | None) -> tuple[str, str]:
    position = target_position.strip()
    description = job_description.strip()
    if profile:
        position = profile.target_position or position or profile.name
        description = profile.requirement_summary or description or profile.description
    return position, description


def delete_record_with_files(db: Session, record: AnalysisRecord) -> int:
    files = db.query(UploadedFile).filter(UploadedFile.analysis_record_id == record.id).all()
    reports = db.query(Report).filter(Report.analysis_record_id == record.id).all()
    for item in files:
        remove_upload_path_if_unreferenced(db, item)
        db.delete(item)
    for report in reports:
        remove_report_path_if_unreferenced(db, report)
        db.delete(report)
    db.flush()
    db.delete(record)
    return record.id


def remove_upload_path_if_unreferenced(db: Session, item: UploadedFile) -> None:
    references = (
        db.query(UploadedFile)
        .filter(UploadedFile.stored_path == item.stored_path, UploadedFile.id != item.id)
        .count()
    )
    if references == 0:
        remove_path(item.stored_path)


def remove_report_path_if_unreferenced(db: Session, report: Report) -> None:
    references = (
        db.query(Report)
        .filter(Report.stored_path == report.stored_path, Report.id != report.id)
        .count()
    )
    if references == 0:
        remove_path(report.stored_path)


def analyze_path(
    db: Session,
    user: User,
    path: Path,
    original_filename: str,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    batch_task_id: int | None = None,
    job_profile_id: int = 0,
    guest_session_id: str | None = None,
    parent_record_id: int | None = None,
) -> dict[str, Any]:
    profile = resolve_job_profile(db, ActorContext(user=user, guest_session_id=guest_session_id), job_profile_id)
    target_position, job_description = resolve_job_inputs(target_position, job_description, profile)
    parsed = ingest_resume(path)
    result = analyze_resume(parsed, target_position, job_description)
    result, mode = enhance_with_deepseek(result, parsed.get("raw_text", ""), enable_ai)
    result["analysis_mode"] = mode
    if profile:
        result["job_profile"] = job_profile_payload(profile)
    sections_payload = dict(parsed["sections"])
    sections_payload["_parse_quality"] = result.get("parse_quality", parsed.get("parse_quality", "medium"))
    sections_payload["_parse_warnings"] = result.get("parse_warnings", parsed.get("parse_warnings", []))
    sections_payload["_blocks"] = parsed.get("blocks", [])
    parent_record = None
    version_no = 1
    root_record_id = None
    if parent_record_id:
        parent_record = db.query(AnalysisRecord).filter(AnalysisRecord.id == parent_record_id).first()
        if parent_record:
            version_no = int(parent_record.version_no or 1) + 1
            root_record_id = parent_record.root_record_id or parent_record.id
    record = AnalysisRecord(
        user_id=user.id,
        guest_session_id=guest_session_id,
        batch_task_id=batch_task_id,
        job_profile_id=profile.id if profile else None,
        parent_record_id=parent_record_id if parent_record else None,
        version_no=version_no,
        root_record_id=root_record_id,
        original_filename=original_filename,
        target_position=result.get("target_position", target_position),
        job_description=job_description,
        total_score=result["total_score"],
        scores_json=dumps(result["scores"]),
        sections_json=dumps(sections_payload),
        diagnosis_json=dumps(result["diagnosis"]),
        suggestions_json=dumps(result["suggestions"]),
        match_result_json=dumps(result["match_result"]),
        analysis_mode=mode,
        status="success",
        error_message=result.get("ai_fallback_reason", ""),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    if not record.root_record_id:
        record.root_record_id = record.id
        db.commit()
        db.refresh(record)
    db.add(
        UploadedFile(
            user_id=user.id,
            guest_session_id=guest_session_id,
            analysis_record_id=record.id,
            batch_task_id=batch_task_id,
            original_filename=original_filename,
            stored_path=str(path),
            file_type=path.suffix.lower(),
            file_size=path.stat().st_size,
        )
    )
    report_paths = generate_reports(record.id, original_filename, result)
    for fmt, report_path in report_paths.items():
        db.add(
            Report(
                user_id=user.id,
                guest_session_id=guest_session_id,
                analysis_record_id=record.id,
                batch_task_id=batch_task_id,
                report_type="single",
                format=fmt,
                stored_path=str(report_path),
            )
        )
    db.commit()
    return record_to_response(record, include_detail=True, db=db)


def record_to_response(record: AnalysisRecord, include_detail: bool, db: Session) -> dict[str, Any]:
    reports = db.query(Report).filter(Report.analysis_record_id == record.id).all()
    report_map = {report.format: report.id for report in reports}
    source_file = get_source_resume_file(db, record.id, record.user_id)
    job_profile = db.query(JobProfile).filter(JobProfile.id == record.job_profile_id).first() if record.job_profile_id else None
    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    parse_quality = sections_payload.pop("_parse_quality", "medium")
    parse_warnings = sections_payload.pop("_parse_warnings", [])
    blocks = sections_payload.pop("_blocks", [])
    if not isinstance(blocks, list):
        blocks = []
    data: dict[str, Any] = {
        "record_id": record.id,
        "filename": record.original_filename,
        "target_position": record.target_position,
        "job_profile": job_profile_payload(job_profile) if job_profile else None,
        "total_score": record.total_score,
        "analysis_mode": record.analysis_mode,
        "analysis_mode_label": mode_label(record.analysis_mode),
        "ai_fallback_reason": record.error_message or "",
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "version_no": int(record.version_no or 1),
        "root_record_id": record.root_record_id or record.id,
        "parent_record_id": record.parent_record_id,
        "reports": report_map,
        "source_resume_url": f"/api/resumes/{record.id}/source" if source_file else "",
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings if isinstance(parse_warnings, list) else [],
    }
    if include_detail:
        scores = loads(record.scores_json, {})
        match_result = loads(record.match_result_json, {})
        if not isinstance(match_result, dict):
            match_result = {}
        data.update(
            {
                "job_description": record.job_description or "",
                "scores": scores,
                "sections": sections_payload,
                "blocks": blocks,
                "diagnosis": loads(record.diagnosis_json, []),
                "suggestions": loads(record.suggestions_json, []),
                "match_result": match_result,
                "evidence_snippets": match_result.get("evidence_snippets", []),
                "matched_keywords": match_result.get("matched_keywords", []),
                "missing_keywords": match_result.get("missing_keywords", []),
                "match_confidence": match_result.get("confidence", 0),
                "target_position_source": match_result.get("target_source", "generic"),
                "chart_data": {
                    "bar": [{"name": score_label(key), "value": value} for key, value in scores.items()],
                    "radar": [{"name": score_label(key), "value": value} for key, value in scores.items()],
                },
            }
        )
    return data


def list_record_versions(record: AnalysisRecord, db: Session) -> list[dict[str, Any]]:
    root_id = record.root_record_id or record.id
    versions = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.root_record_id == root_id, AnalysisRecord.user_id == record.user_id)
        .order_by(AnalysisRecord.version_no.asc(), AnalysisRecord.created_at.asc())
        .all()
    )
    return [
        {
            "record_id": item.id,
            "version_no": int(item.version_no or 1),
            "filename": item.original_filename,
            "total_score": item.total_score,
            "created_at": item.created_at.isoformat() if item.created_at else "",
            "is_current": item.id == record.id,
        }
        for item in versions
    ]


def build_version_compare(record_a: AnalysisRecord, record_b: AnalysisRecord) -> dict[str, Any]:
    scores_a = loads(record_a.scores_json, {})
    scores_b = loads(record_b.scores_json, {})
    if not isinstance(scores_a, dict):
        scores_a = {}
    if not isinstance(scores_b, dict):
        scores_b = {}
    keys = sorted(set(scores_a) | set(scores_b))
    dimension_deltas = [
        {
            "name": score_label(key),
            "key": key,
            "a": float(scores_a.get(key, 0) or 0),
            "b": float(scores_b.get(key, 0) or 0),
            "delta": round(float(scores_b.get(key, 0) or 0) - float(scores_a.get(key, 0) or 0), 1),
        }
        for key in keys
    ]
    total_a = float(record_a.total_score or 0)
    total_b = float(record_b.total_score or 0)
    return {
        "a": {
            "record_id": record_a.id,
            "version_no": int(record_a.version_no or 1),
            "filename": record_a.original_filename,
            "total_score": total_a,
            "created_at": record_a.created_at.isoformat() if record_a.created_at else "",
        },
        "b": {
            "record_id": record_b.id,
            "version_no": int(record_b.version_no or 1),
            "filename": record_b.original_filename,
            "total_score": total_b,
            "created_at": record_b.created_at.isoformat() if record_b.created_at else "",
        },
        "summary": {
            "total_score_delta": round(total_b - total_a, 1),
            "improved": total_b > total_a,
            "unchanged": total_b == total_a,
        },
        "dimension_deltas": dimension_deltas,
        "trend": [
            {
                "version_no": int(item.version_no or 1),
                "record_id": item.id,
                "total_score": float(item.total_score or 0),
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
            for item in sorted(
                {record_a.id: record_a, record_b.id: record_b}.values(),
                key=lambda item: (int(item.version_no or 1), item.created_at.isoformat() if item.created_at else ""),
            )
        ],
    }


def process_batch_task(
    batch_task_id: int,
    user_id: int,
    zip_path_str: str,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    job_profile_id: int | None = None,
    guest_session_id: str | None = None,
) -> None:
    zip_path = Path(zip_path_str)
    extract_dir: Path | None = None
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        batch = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
        if not user or not batch:
            return

        try:
            extracted = safe_extract_zip(zip_path)
            extract_dir = extracted[0].parent if extracted else None
            batch.total_files = len(extracted)
            batch.summary_json = dumps([])
            db.commit()
        except Exception as exc:
            batch.status = "failed"
            batch.summary_json = dumps(
                [{"filename": zip_path.name, "status": "failed", "error": str(exc), "parse_quality": "low", "parse_warnings": [str(exc)]}]
            )
            batch.failed_count = 1
            batch.success_count = 0
            batch.total_files = 0
            db.commit()
            return

        results: list[dict[str, Any]] = []
        success = 0
        failed = 0

        try:
            for path in extracted:
                db.refresh(batch)
                if batch.status == "paused":
                    return
                if path.name.startswith("~$"):
                    failed += 1
                    results.append(
                        {
                            "filename": path.name,
                            "status": "skipped",
                            "error": "Word 临时文件，已跳过",
                            "parse_quality": "low",
                            "parse_warnings": ["Word 临时文件不是正式简历，系统已跳过。"],
                        }
                    )
                    batch.success_count = success
                    batch.failed_count = failed
                    batch.summary_json = dumps(results)
                    batch.status = "processing"
                    db.commit()
                    continue
                try:
                    item = analyze_path(
                        db,
                        user,
                        path,
                        path.name,
                        target_position,
                        job_description,
                        enable_ai,
                        batch.id,
                        job_profile_id or 0,
                        guest_session_id=guest_session_id,
                    )
                    success += 1
                    results.append(
                        {
                            "filename": path.name,
                            "status": "success",
                            "record_id": item["record_id"],
                            "total_score": item["total_score"],
                            "analysis_mode": item.get("analysis_mode", ""),
                            "analysis_mode_label": item.get("analysis_mode_label", ""),
                            "parse_quality": item.get("parse_quality", "medium"),
                            "parse_warnings": item.get("parse_warnings", []),
                        }
                    )
                except Exception as exc:
                    failed += 1
                    results.append({"filename": path.name, "status": "failed", "error": str(exc), "parse_quality": "low", "parse_warnings": [str(exc)]})

                batch.success_count = success
                batch.failed_count = failed
                batch.summary_json = dumps(results)
                batch.status = "processing"
                db.commit()

            batch.success_count = success
            batch.failed_count = failed
            batch.summary_json = dumps(results)
            if failed and success:
                batch.status = "partial_success"
            elif failed and not success:
                batch.status = "failed"
            else:
                batch.status = "success"
            db.commit()
        finally:
            if extract_dir and extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)


def retry_batch_processing(batch: BatchTask, user: User, background_tasks, db: Session) -> dict[str, Any]:
    zip_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.batch_task_id == batch.id)
        .order_by(UploadedFile.id.desc())
        .first()
    )
    if not zip_file:
        raise HTTPException(status_code=400, detail="找不到批量任务的原始 ZIP 文件。")
    zip_path = Path(zip_file.stored_path)
    if not zip_path.exists():
        raise HTTPException(status_code=400, detail="原始 ZIP 文件已丢失，无法重试。")

    profile = db.query(JobProfile).filter(JobProfile.id == batch.job_profile_id).first() if batch.job_profile_id else None
    target_position = profile.target_position if profile else ""
    job_description = (profile.requirement_summary or profile.description) if profile else ""

    batch.status = "processing"
    batch.success_count = 0
    batch.failed_count = 0
    batch.total_files = 0
    batch.summary_json = dumps([])
    db.commit()
    db.refresh(batch)

    from app.api.task_dispatch import dispatch_batch_task

    dispatch_batch_task(
        background_tasks,
        batch_task_id=batch.id,
        user_id=user.id,
        zip_path_str=str(zip_path),
        target_position=target_position,
        job_description=job_description,
        enable_ai=True,
        job_profile_id=profile.id if profile else None,
        guest_session_id=batch.guest_session_id,
    )
    return batch_to_response(batch, include_results=True, db=db)


def batch_to_response(batch: BatchTask, include_results: bool, db: Session) -> dict[str, Any]:
    results = loads(batch.summary_json, [])
    if not isinstance(results, list):
        results = []
    processed_files = int(batch.success_count or 0) + int(batch.failed_count or 0)
    job_profile = db.query(JobProfile).filter(JobProfile.id == batch.job_profile_id).first() if batch.job_profile_id else None
    data: dict[str, Any] = {
        "batch_task_id": batch.id,
        "job_profile": job_profile_payload(job_profile) if job_profile else None,
        "filename": batch.zip_filename,
        "status": batch.status,
        "status_label": batch_status_label(batch.status),
        "total_files": batch.total_files,
        "processed_files": processed_files,
        "success_count": batch.success_count,
        "failed_count": batch.failed_count,
        "created_at": batch.created_at.isoformat(),
    }
    if include_results:
        data["results"] = results
    return data


def list_task_center(actor: ActorContext, db: Session) -> dict[str, Any]:
    batch_rows = scope_batches(db.query(BatchTask), actor).order_by(BatchTask.created_at.desc()).limit(100).all()
    single_rows = (
        scope_records(db.query(AnalysisRecord), actor)
        .filter(AnalysisRecord.batch_task_id.is_(None))
        .order_by(AnalysisRecord.created_at.desc())
        .limit(100)
        .all()
    )
    batch_items = [
        {
            "task_key": f"batch-{item.id}",
            "task_type": "batch_analysis",
            "task_type_label": "批量分析",
            "batch_task_id": item.id,
            "record_id": None,
            "status": item.status,
            "status_label": batch_status_label(item.status),
            "filename": item.zip_filename,
            "target_position": "",
            "total_score": None,
            "processed_files": int(item.success_count or 0) + int(item.failed_count or 0),
            "total_files": item.total_files,
            "success_count": item.success_count,
            "failed_count": item.failed_count,
            "job_profile": job_profile_payload(db.query(JobProfile).filter(JobProfile.id == item.job_profile_id).first()) if item.job_profile_id else None,
            "created_at": item.created_at.isoformat() if item.created_at else "",
        }
        for item in batch_rows
    ]
    single_items = [
        {
            "task_key": f"record-{item.id}",
            "task_type": "single_analysis",
            "task_type_label": "单份分析",
            "batch_task_id": None,
            "record_id": item.id,
            "status": item.status,
            "status_label": batch_status_label(item.status if item.status in {"pending", "processing", "failed"} else "success"),
            "filename": item.original_filename,
            "target_position": item.target_position,
            "total_score": item.total_score,
            "processed_files": 1,
            "total_files": 1,
            "success_count": 1 if item.status == "success" else 0,
            "failed_count": 1 if item.status == "failed" else 0,
            "job_profile": job_profile_payload(db.query(JobProfile).filter(JobProfile.id == item.job_profile_id).first()) if item.job_profile_id else None,
            "created_at": item.created_at.isoformat() if item.created_at else "",
        }
        for item in single_rows
    ]
    items = sorted(batch_items + single_items, key=lambda item: item["created_at"], reverse=True)
    summary = {"pending": 0, "processing": 0, "paused": 0, "success": 0, "failed": 0, "partial_success": 0}
    for item in items:
        status = item["status"]
        summary[status] = summary.get(status, 0) + 1
    return {"summary": summary, "tasks": items}


def list_report_center(actor: ActorContext, db: Session) -> list[dict[str, Any]]:
    records = scope_records(db.query(AnalysisRecord), actor).order_by(AnalysisRecord.created_at.desc()).limit(200).all()
    items: list[dict[str, Any]] = []
    for record in records:
        reports = db.query(Report).filter(Report.analysis_record_id == record.id).all()
        if not reports:
            continue
        report_map = {report.format: report.id for report in reports}
        profile = db.query(JobProfile).filter(JobProfile.id == record.job_profile_id).first() if record.job_profile_id else None
        source_file = get_source_resume_file(db, record.id, record.user_id)
        items.append(
            {
                "record_id": record.id,
                "filename": record.original_filename,
                "target_position": record.target_position,
                "job_profile": job_profile_payload(profile) if profile else None,
                "total_score": record.total_score,
                "analysis_mode": record.analysis_mode,
                "analysis_mode_label": mode_label(record.analysis_mode),
                "status": record.status,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "reports": report_map,
                "available_formats": sorted(report_map.keys()),
                "source_resume_url": f"/api/resumes/{record.id}/source" if source_file else "",
            }
        )
    return items


def get_source_resume_file(db: Session, record_id: int, user_id: int) -> UploadedFile | None:
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.analysis_record_id == record_id, UploadedFile.user_id == user_id)
        .order_by(UploadedFile.id.asc())
        .first()
    )


def resume_media_type(suffix: str) -> str:
    mapping = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return mapping.get(suffix, "application/octet-stream")


def score_label(key: str) -> str:
    labels = {
        "content_completeness": "内容完整性",
        "experience_match": "经历匹配度",
        "language_professionalism": "语言专业性",
        "format_standardization": "格式规范性",
        "highlight_strength": "亮点突出度",
        "job_match": "岗位匹配度",
    }
    return labels.get(key, key)


def mode_label(mode: str) -> str:
    labels = {
        "deepseek": "DeepSeek 已使用",
        "offline_fallback": "DeepSeek 不可用，已回退离线规则分析",
        "offline": "离线规则分析",
    }
    return labels.get(mode, mode)


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


def import_guest_records(request: Request, db: Session) -> dict[str, int]:
    user = require_login(request, db)
    guest = default_user(db)
    if user.id == guest.id:
        raise HTTPException(status_code=400, detail="游客模式不能导入游客历史")
    session_id = guest_session_id_from_request(request)
    if not session_id:
        return {"imported_count": 0}
    guest_records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == guest.id, AnalysisRecord.guest_session_id == session_id)
        .all()
    )
    imported_count = 0
    for record in guest_records:
        duplicate = (
            db.query(AnalysisRecord)
            .filter(
                AnalysisRecord.user_id == user.id,
                AnalysisRecord.original_filename == record.original_filename,
                AnalysisRecord.created_at == record.created_at,
                AnalysisRecord.total_score == record.total_score,
            )
            .first()
        )
        if duplicate:
            continue
        copied_record = AnalysisRecord(
            user_id=user.id,
            guest_session_id=None,
            batch_task_id=None,
            job_profile_id=record.job_profile_id,
            root_record_id=record.root_record_id or record.id,
            parent_record_id=record.parent_record_id,
            version_no=record.version_no,
            original_filename=record.original_filename,
            target_position=record.target_position,
            job_description=record.job_description,
            total_score=record.total_score,
            scores_json=record.scores_json,
            sections_json=record.sections_json,
            diagnosis_json=record.diagnosis_json,
            suggestions_json=record.suggestions_json,
            match_result_json=record.match_result_json,
            analysis_mode=record.analysis_mode,
            status=record.status,
            error_message=record.error_message,
            created_at=record.created_at,
        )
        db.add(copied_record)
        db.flush()
        files = db.query(UploadedFile).filter(UploadedFile.analysis_record_id == record.id).all()
        for item in files:
            db.add(
                UploadedFile(
                    user_id=user.id,
                    analysis_record_id=copied_record.id,
                    batch_task_id=None,
                    original_filename=item.original_filename,
                    stored_path=item.stored_path,
                    file_type=item.file_type,
                    file_size=item.file_size,
                    created_at=item.created_at,
                )
            )
        reports = db.query(Report).filter(Report.analysis_record_id == record.id).all()
        for report in reports:
            db.add(
                Report(
                    user_id=user.id,
                    analysis_record_id=copied_record.id,
                    batch_task_id=None,
                    report_type=report.report_type,
                    format=report.format,
                    stored_path=report.stored_path,
                    created_at=report.created_at,
                )
            )
        imported_count += 1
    db.commit()
    return {"imported_count": imported_count}


def build_admin_stats(admin: User, db: Session) -> dict[str, Any]:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "admin": user_payload(admin),
        "users": {
            "total": db.query(User).count(),
            "active": db.query(User).filter(User.status == "active").count(),
            "disabled": db.query(User).filter(User.status == "disabled").count(),
            "admins": db.query(User).filter(User.role == "admin").count(),
            "teachers": db.query(User).filter(User.role == "teacher").count(),
        },
        "records": {
            "total": db.query(AnalysisRecord).count(),
            "today": db.query(AnalysisRecord).filter(AnalysisRecord.created_at >= today_start).count(),
        },
        "batch_tasks": {
            "total": db.query(BatchTask).count(),
            "processing": db.query(BatchTask).filter(BatchTask.status.in_(["pending", "processing"])).count(),
        },
        "reports": {
            "total": db.query(Report).count(),
        },
        "audit_logs": {
            "total": db.query(AuditLog).count(),
        },
    }


def build_teacher_stats(user: User, db: Session) -> dict[str, Any]:
    from app.models.entities import UserProfile

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    records = db.query(AnalysisRecord).filter(AnalysisRecord.status == "success").all()
    score_buckets = {"0-59": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90-100": 0}
    for record in records:
        score = float(record.total_score or 0)
        if score < 60:
            score_buckets["0-59"] += 1
        elif score < 70:
            score_buckets["60-69"] += 1
        elif score < 80:
            score_buckets["70-79"] += 1
        elif score < 90:
            score_buckets["80-89"] += 1
        else:
            score_buckets["90-100"] += 1

    daily_rows = (
        db.query(func.date(AnalysisRecord.created_at).label("day"), func.count(AnalysisRecord.id))
        .filter(AnalysisRecord.created_at >= week_start)
        .group_by(func.date(AnalysisRecord.created_at))
        .order_by(func.date(AnalysisRecord.created_at))
        .all()
    )
    daily_volume = [{"date": str(day), "count": int(count)} for day, count in daily_rows]

    school_rows = (
        db.query(UserProfile.school, func.count(UserProfile.id))
        .filter(UserProfile.school != "")
        .group_by(UserProfile.school)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )
    major_rows = (
        db.query(UserProfile.major, func.count(UserProfile.id))
        .filter(UserProfile.major != "")
        .group_by(UserProfile.major)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )
    grade_rows = (
        db.query(UserProfile.grade, func.count(UserProfile.id))
        .filter(UserProfile.grade != "")
        .group_by(UserProfile.grade)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )

    job_rows = (
        db.query(JobProfile.name, func.count(AnalysisRecord.id))
        .join(AnalysisRecord, AnalysisRecord.job_profile_id == JobProfile.id)
        .group_by(JobProfile.name)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(8)
        .all()
    )

    profile_count = db.query(UserProfile).filter(
        (UserProfile.school != "") | (UserProfile.major != "") | (UserProfile.grade != "")
    ).count()

    return {
        "viewer": user_payload(user),
        "summary": {
            "students_with_profile": profile_count,
            "total_records": len(records),
            "today_records": db.query(AnalysisRecord).filter(AnalysisRecord.created_at >= today_start).count(),
            "week_records": db.query(AnalysisRecord).filter(AnalysisRecord.created_at >= week_start).count(),
            "avg_score": round(sum(float(r.total_score or 0) for r in records) / max(len(records), 1), 1),
        },
        "score_distribution": [{"band": band, "count": count} for band, count in score_buckets.items()],
        "daily_volume": daily_volume,
        "by_school": [{"name": name or "未填写", "count": int(count)} for name, count in school_rows],
        "by_major": [{"name": name or "未填写", "count": int(count)} for name, count in major_rows],
        "by_grade": [{"name": name or "未填写", "count": int(count)} for name, count in grade_rows],
        "top_job_profiles": [{"name": name, "count": int(count)} for name, count in job_rows],
    }


def list_admin_users(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(
            User,
            func.count(func.distinct(AnalysisRecord.id)).label("record_count"),
            func.count(func.distinct(BatchTask.id)).label("batch_count"),
        )
        .outerjoin(AnalysisRecord, AnalysisRecord.user_id == User.id)
        .outerjoin(BatchTask, BatchTask.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [admin_user_payload(user, record_count, batch_count) for user, record_count, batch_count in rows]


def list_admin_records(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(AnalysisRecord, User)
        .join(User, User.id == AnalysisRecord.user_id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(500)
        .all()
    )
    profile_ids = {record.job_profile_id for record, _ in rows if record.job_profile_id}
    profile_map = {profile.id: profile.name for profile in db.query(JobProfile).filter(JobProfile.id.in_(profile_ids)).all()} if profile_ids else {}
    for record, _ in rows:
        setattr(record, "_job_profile_name", profile_map.get(record.job_profile_id, ""))
    return [admin_record_payload(record, user) for record, user in rows]


def list_admin_audit_logs(db: Session) -> list[dict[str, Any]]:
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [audit_log_payload(log) for log in logs]


def delete_history_record(record_id: int, request: Request, db: Session) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    try:
        delete_record_with_files(db, record)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="无法删除记录，可能仍存在关联数据。") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="无法删除记录，请稍后再试。") from exc
    return {"deleted": True, "record_id": record_id}


def download_report_file(report_id: int, request: Request, format: str, db: Session) -> FileResponse:
    actor = resolve_actor(request, db)
    report = db.query(Report).filter(Report.id == report_id, Report.format == format).first()
    if not report or report.user_id != actor.user.id:
        raise HTTPException(status_code=404, detail="报告不存在。")
    if actor.is_guest and report.guest_session_id != actor.guest_session_id:
        raise HTTPException(status_code=404, detail="报告不存在。")
    path = Path(report.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在。")
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media_type, filename=path.name)
