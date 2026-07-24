from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.actor import (
    ActorContext,
    current_user_from_request,
    guest_session_id_from_request,
    record_owned_by_actor,
    resolve_actor,
    scope_batches,
    scope_job_profiles,
    scope_records,
)
from app.api.auth_context import (
    active_admin_count,
    auth_response,
    clear_session_cookie,
    client_ip,
    current_actor,
    default_user,
    generate_temp_password,
    require_admin,
    require_login,
    require_teacher_or_admin,
    set_session_cookie,
    write_audit,
)
from app.api.serializers import (
    admin_record_payload,
    admin_user_payload,
    audit_log_payload,
    batch_status_label,
    job_profile_payload,
    mode_label,
    normalize_job_profile_payload,
    public_analysis_mode_label,
    user_payload,
)
from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, BatchTask, JobProfile, Report, UploadedFile, User
from app.services.analysis_pipeline import resolve_job_inputs as _resolve_job_inputs, run_analysis_pipeline
from app.services.ai import enhance_with_deepseek
from app.services.batch_service import batch_to_response, process_batch_task, retry_batch_processing
from app.services.interview_engine import build_interview_prep, build_mock_interview_session
from app.services.report import ensure_report_file, generate_reports, generate_rewrite_report
from app.services.scoring import label_for_score
from app.services.pipeline_utils import label_for_section
from app.services.score_engine import build_evidence
from app.services.score_engine import WEIGHTS
from app.services.stats_service import (
    build_admin_stats,
    build_teacher_stats,
    list_admin_audit_logs,
    list_admin_records,
    list_admin_users,
)
from app.services.storage import remove_path
from app.utils.json_tools import dumps, loads

logger = logging.getLogger("uvicorn.error")

__all__ = [
    "active_admin_count",
    "admin_record_payload",
    "admin_user_payload",
    "analyze_path",
    "audit_log_payload",
    "auth_response",
    "batch_status_label",
    "batch_to_response",
    "build_admin_stats",
    "build_teacher_stats",
    "build_version_compare",
    "clear_session_cookie",
    "client_ip",
    "create_single_analysis_job",
    "current_actor",
    "current_user_from_request",
    "default_user",
    "delete_history_record",
    "delete_record_with_files",
    "download_report_file",
    "download_rewrite_report_file",
    "generate_temp_password",
    "get_source_resume_file",
    "import_guest_records",
    "job_profile_payload",
    "list_admin_audit_logs",
    "list_admin_records",
    "list_admin_users",
    "list_record_versions",
    "list_report_center",
    "list_task_center",
    "mode_label",
    "normalize_job_profile_payload",
    "process_batch_task",
    "process_ai_enhancement",
    "process_single_analysis",
    "record_to_response",
    "records_to_response",
    "refresh_interview_prep",
    "refresh_rewrite_preview",
    "require_admin",
    "require_login",
    "require_teacher_or_admin",
    "resolve_job_inputs",
    "resolve_job_profile",
    "resume_media_type",
    "retry_batch_processing",
    "retry_single_analysis",
    "set_session_cookie",
    "user_payload",
    "write_audit",
]


AI_STATUS_NONE = "none"
AI_STATUS_PENDING = "pending"
AI_STATUS_PROCESSING = "processing"
AI_STATUS_SUCCESS = "success"
AI_STATUS_FAILED = "failed"
AI_PROCESSING_STALE_SECONDS = 75
AI_MAX_AUTO_REQUEUE = 2


def _sections_payload(record: AnalysisRecord) -> dict[str, Any]:
    payload = loads(record.sections_json, {})
    return payload if isinstance(payload, dict) else {}


def _ai_status_from_sections(sections: dict[str, Any]) -> str:
    status = str(sections.get("_ai_enhancement_status") or AI_STATUS_NONE)
    return status if status in {AI_STATUS_NONE, AI_STATUS_PENDING, AI_STATUS_PROCESSING, AI_STATUS_SUCCESS, AI_STATUS_FAILED} else AI_STATUS_NONE


def _set_ai_status(sections: dict[str, Any], status: str, error: str = "") -> None:
    sections["_ai_enhancement_status"] = status
    sections["_ai_enhancement_error"] = error
    if status == AI_STATUS_PROCESSING:
        sections["_ai_enhancement_started_at"] = datetime.utcnow().isoformat()
        try:
            sections["_ai_enhancement_attempts"] = int(sections.get("_ai_enhancement_attempts") or 0) + 1
        except (TypeError, ValueError):
            sections["_ai_enhancement_attempts"] = 1
    else:
        sections.pop("_ai_enhancement_started_at", None)


def _ai_processing_is_stale(sections: dict[str, Any]) -> bool:
    if _ai_status_from_sections(sections) != AI_STATUS_PROCESSING:
        return False
    raw_started_at = str(sections.get("_ai_enhancement_started_at") or "")
    if not raw_started_at:
        return True
    try:
        started_at = datetime.fromisoformat(raw_started_at)
    except ValueError:
        return True
    return datetime.utcnow() - started_at > timedelta(seconds=AI_PROCESSING_STALE_SECONDS)


def recover_stale_ai_enhancement(record: AnalysisRecord, db: Session) -> None:
    sections = _sections_payload(record)
    if not sections.get("_ai_requested") or not _ai_processing_is_stale(sections):
        return
    try:
        attempts = int(sections.get("_ai_enhancement_attempts") or 0)
    except (TypeError, ValueError):
        attempts = 0
    if attempts >= AI_MAX_AUTO_REQUEUE:
        _set_ai_status(sections, AI_STATUS_FAILED, "AI 深度优化超时，请在详情页点击“生成 AI 深度改写”按需重试。")
        record.sections_json = dumps(sections)
        db.commit()
        return
    _set_ai_status(sections, AI_STATUS_PENDING, "AI 增强任务中断，已自动重新排队。")
    record.sections_json = dumps(sections)
    db.commit()
    queue_ai_enhancement(record.id)


def _should_queue_ai_enhancement(record: AnalysisRecord) -> bool:
    sections = _sections_payload(record)
    return bool(sections.get("_ai_requested")) and _ai_status_from_sections(sections) == AI_STATUS_PENDING


def queue_ai_enhancement(record_id: int) -> None:
    from app.tasks.celery_app import celery_enabled

    if celery_enabled():
        from app.tasks.batch_worker import process_ai_enhancement_celery

        process_ai_enhancement_celery.delay(record_id)
        return

    thread = threading.Thread(target=process_ai_enhancement, args=(record_id,), daemon=True)
    thread.start()


def resolve_job_profile(db: Session, actor: ActorContext, job_profile_id: int) -> JobProfile | None:
    if not job_profile_id or job_profile_id <= 0:
        return None
    profile = scope_job_profiles(db.query(JobProfile), actor).filter(JobProfile.id == job_profile_id, JobProfile.status != "archived").first()
    if not profile:
        raise HTTPException(status_code=404, detail="所选岗位模板不存在。")
    return profile


def resolve_job_inputs(target_position: str, job_description: str, profile: JobProfile | None) -> tuple[str, str]:
    return _resolve_job_inputs(target_position, job_description, profile)


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
    batch_file_count = 1
    if batch_task_id:
        batch_row = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
        if batch_row and batch_row.total_files:
            batch_file_count = int(batch_row.total_files)
    pipeline = _run_analysis_pipeline(
        path,
        target_position,
        job_description,
        enable_ai,
        profile,
        batch_file_count=batch_file_count,
    )
    result = pipeline["result"]
    parent_id, version_no, root_record_id = _resolve_version_info(db, parent_record_id)
    record = AnalysisRecord(
        user_id=user.id,
        guest_session_id=guest_session_id,
        batch_task_id=batch_task_id,
        job_profile_id=profile.id if profile else None,
        parent_record_id=parent_id,
        version_no=version_no,
        root_record_id=root_record_id,
        original_filename=original_filename,
        target_position=result.get("target_position", pipeline["target_position"]),
        job_description=pipeline["job_description"],
        total_score=result["total_score"],
        scores_json=dumps(result["scores"]),
        sections_json=dumps(pipeline["sections_payload"]),
        diagnosis_json=dumps(result["diagnosis"]),
        suggestions_json=dumps(result["suggestions"]),
        match_result_json=dumps(result["match_result"]),
        analysis_mode=pipeline["mode"],
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
    db.commit()
    if _should_queue_ai_enhancement(record):
        queue_ai_enhancement(record.id)
    include_detail = batch_task_id is None
    return record_to_response(record, include_detail=include_detail, db=db)


def _run_analysis_pipeline(
    path: Path,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    profile: JobProfile | None,
    *,
    batch_file_count: int = 1,
) -> dict[str, Any]:
    return run_analysis_pipeline(
        path,
        target_position,
        job_description,
        enable_ai,
        profile,
        batch_file_count=batch_file_count,
    )


def _resolve_version_info(db: Session, parent_record_id: int | None) -> tuple[int | None, int, int | None]:
    if not parent_record_id:
        return None, 1, None
    parent_record = db.query(AnalysisRecord).filter(AnalysisRecord.id == parent_record_id).first()
    if not parent_record:
        return None, 1, None
    return parent_record_id, int(parent_record.version_no or 1) + 1, parent_record.root_record_id or parent_record.id


def _attach_reports(
    db: Session,
    record: AnalysisRecord,
    original_filename: str,
    result: dict[str, Any],
    batch_task_id: int | None,
    *,
    formats: list[str] | None = None,
) -> None:
    if formats is None:
        formats = ["docx"]
    report_paths = generate_reports(record.id, original_filename, result, formats=formats)
    for fmt, report_path in report_paths.items():
        db.add(
            Report(
                user_id=record.user_id,
                guest_session_id=record.guest_session_id,
                analysis_record_id=record.id,
                batch_task_id=batch_task_id,
                report_type="single",
                format=fmt,
                stored_path=str(report_path),
            )
        )


def create_single_analysis_job(
    db: Session,
    user: User,
    path: Path,
    original_filename: str,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    job_profile_id: int = 0,
    guest_session_id: str | None = None,
    parent_record_id: int | None = None,
) -> AnalysisRecord:
    profile = resolve_job_profile(db, ActorContext(user=user, guest_session_id=guest_session_id), job_profile_id)
    target_position, job_description = resolve_job_inputs(target_position, job_description, profile)
    parent_id, version_no, root_record_id = _resolve_version_info(db, parent_record_id)
    record = AnalysisRecord(
        user_id=user.id,
        guest_session_id=guest_session_id,
        job_profile_id=profile.id if profile else None,
        parent_record_id=parent_id,
        version_no=version_no,
        root_record_id=root_record_id,
        original_filename=original_filename,
        target_position=target_position,
        job_description=job_description,
        total_score=0,
        status="processing",
        analysis_mode="offline",
        sections_json=dumps({"_job": {"enable_ai": enable_ai}}),
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
            original_filename=original_filename,
            stored_path=str(path),
            file_type=path.suffix.lower(),
            file_size=path.stat().st_size,
        )
    )
    db.commit()
    db.refresh(record)
    return record


def process_single_analysis(record_id: int) -> None:
    with SessionLocal() as db:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
        if not record or record.status != "processing":
            return
        upload = get_source_resume_file(db, record.id, record.user_id)
        if not upload or not Path(upload.stored_path).exists():
            record.status = "failed"
            record.error_message = "找不到原始简历文件。"
            db.commit()
            return
        path = Path(upload.stored_path)
        job_meta = loads(record.sections_json, {}).get("_job", {})
        if not isinstance(job_meta, dict):
            job_meta = {}
        enable_ai = bool(job_meta.get("enable_ai", True))
        profile = (
            db.query(JobProfile).filter(JobProfile.id == record.job_profile_id).first()
            if record.job_profile_id
            else None
        )
        try:
            pipeline = _run_analysis_pipeline(path, record.target_position, record.job_description, enable_ai, profile)
            result = pipeline["result"]
            record.target_position = result.get("target_position", record.target_position)
            record.total_score = result["total_score"]
            record.scores_json = dumps(result["scores"])
            record.sections_json = dumps(pipeline["sections_payload"])
            record.diagnosis_json = dumps(result["diagnosis"])
            record.suggestions_json = dumps(result["suggestions"])
            record.match_result_json = dumps(result["match_result"])
            record.analysis_mode = pipeline["mode"]
            record.error_message = result.get("ai_fallback_reason", "")
            record.status = "success"
            db.commit()
            if _should_queue_ai_enhancement(record):
                queue_ai_enhancement(record.id)
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)
        db.commit()


def process_ai_enhancement(record_id: int) -> None:
    started = perf_counter()
    with SessionLocal() as db:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
        if not record or record.status != "success":
            return

        sections_payload = _sections_payload(record)
        if _ai_status_from_sections(sections_payload) not in {AI_STATUS_PENDING, AI_STATUS_FAILED}:
            return
        if not sections_payload.get("_ai_requested"):
            return

        _set_ai_status(sections_payload, AI_STATUS_PROCESSING)
        record.sections_json = dumps(sections_payload)
        db.commit()

        try:
            sections = {key: value for key, value in sections_payload.items() if not str(key).startswith("_") and isinstance(value, list)}
            resume_text = "\n".join(
                str(line)
                for lines in sections.values()
                for line in (lines if isinstance(lines, list) else [])
                if str(line).strip()
            )
            match_result = loads(record.match_result_json, {})
            if not isinstance(match_result, dict):
                match_result = {}
            scores = loads(record.scores_json, {})
            if not isinstance(scores, dict):
                scores = {}
            diagnosis = loads(record.diagnosis_json, [])
            if not isinstance(diagnosis, list):
                diagnosis = []
            suggestions = loads(record.suggestions_json, [])
            if not isinstance(suggestions, list):
                suggestions = []

            result = {
                "target_position": record.target_position or match_result.get("target_position", ""),
                "target_position_source": match_result.get("target_source", "generic"),
                "total_score": record.total_score,
                "scores": scores,
                "sections": sections,
                "diagnosis": diagnosis,
                "suggestions": suggestions,
                "structured_suggestions": sections_payload.get("_structured_suggestions", []),
                "match_result": match_result,
                "rewrite_preview": sections_payload.get("_rewrite_preview", {}),
                "parse_quality": sections_payload.get("_parse_quality", "medium"),
                "parse_warnings": sections_payload.get("_parse_warnings", []),
                "score_reliability": sections_payload.get("_score_reliability", "normal"),
                "evidence": build_evidence(sections, resume_text),
            }
            enhanced, mode = enhance_with_deepseek(result, resume_text, True)
            if mode != "deepseek":
                error = str(enhanced.get("ai_fallback_reason") or "AI 增强未生成有效结果。")
                _set_ai_status(sections_payload, AI_STATUS_FAILED, error)
                record.sections_json = dumps(sections_payload)
                db.commit()
                return

            record.diagnosis_json = dumps(enhanced.get("diagnosis", diagnosis))
            record.suggestions_json = dumps(enhanced.get("suggestions", suggestions))
            sections_payload["_structured_suggestions"] = enhanced.get("structured_suggestions", sections_payload.get("_structured_suggestions", []))
            sections_payload["_rewrite_preview"] = enhanced.get("rewrite_preview", sections_payload.get("_rewrite_preview", {}))
            _set_ai_status(sections_payload, AI_STATUS_SUCCESS)
            record.sections_json = dumps(sections_payload)
            record.analysis_mode = mode
            record.error_message = ""
            db.commit()
        except Exception as exc:
            sections_payload = _sections_payload(record)
            _set_ai_status(sections_payload, AI_STATUS_FAILED, str(exc))
            record.sections_json = dumps(sections_payload)
            db.commit()
        finally:
            logger.info(
                "ai_enhancement_timing record_id=%s elapsed_ms=%.0f",
                record_id,
                (perf_counter() - started) * 1000,
            )


def retry_single_analysis(record: AnalysisRecord, background_tasks, db: Session) -> dict[str, Any]:
    if record.status not in {"failed", "paused"}:
        raise HTTPException(status_code=400, detail="只有失败或暂停的单份任务可以重试。")
    record.status = "processing"
    record.error_message = ""
    record.total_score = 0
    sections = loads(record.sections_json, {})
    if not isinstance(sections, dict):
        sections = {}
    sections.setdefault("_job", {"enable_ai": True})
    record.sections_json = dumps(sections)
    db.commit()
    db.refresh(record)
    from app.api.task_dispatch import dispatch_single_analysis

    dispatch_single_analysis(background_tasks, record.id)
    return record_to_response(record, include_detail=False, db=db)


def prefetch_record_context(db: Session, records: list[AnalysisRecord]) -> dict[str, Any]:
    if not records:
        return {"reports": {}, "profiles": {}, "sources": {}}
    record_ids = [record.id for record in records]
    profile_ids = {record.job_profile_id for record in records if record.job_profile_id}

    reports_map: dict[int, dict[str, int]] = {}
    for report in db.query(Report).filter(Report.analysis_record_id.in_(record_ids)).all():
        reports_map.setdefault(report.analysis_record_id, {})[report.format] = report.id

    profiles_map: dict[int, JobProfile] = {}
    if profile_ids:
        for profile in db.query(JobProfile).filter(JobProfile.id.in_(profile_ids)).all():
            profiles_map[profile.id] = profile

    sources_map: dict[int, UploadedFile] = {}
    for uploaded in (
        db.query(UploadedFile)
        .filter(UploadedFile.analysis_record_id.in_(record_ids))
        .order_by(UploadedFile.id.asc())
        .all()
    ):
        sources_map.setdefault(uploaded.analysis_record_id, uploaded)

    return {"reports": reports_map, "profiles": profiles_map, "sources": sources_map}


def prefetch_job_profiles(db: Session, profile_ids: set[int]) -> dict[int, JobProfile]:
    if not profile_ids:
        return {}
    return {profile.id: profile for profile in db.query(JobProfile).filter(JobProfile.id.in_(profile_ids)).all()}


def records_to_response(records: list[AnalysisRecord], include_detail: bool, db: Session) -> list[dict[str, Any]]:
    ctx = prefetch_record_context(db, records)
    return [record_to_response(record, include_detail=include_detail, db=db, ctx=ctx) for record in records]


def _normalize_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        section = str(block.get("section") or "")
        lines = block.get("lines") if isinstance(block.get("lines"), list) else []
        confidence = float(block.get("confidence") or 0)
        item = {
            **block,
            "section": section,
            "section_label": block.get("section_label") or label_for_section(section),
            "lines": lines,
            "line_count": block.get("line_count") or len(lines),
            "preview": block.get("preview") or (next((str(line).strip() for line in lines if str(line).strip()), "")[:120]),
            "confidence_label": block.get("confidence_label")
            or ("识别较完整" if confidence >= 0.85 else "基本识别" if confidence >= 0.65 else "识别偏弱"),
        }
        normalized.append(item)
    return normalized


def record_status_response(record: AnalysisRecord, db: Session) -> dict[str, Any]:
    recover_stale_ai_enhancement(record, db)
    ctx = prefetch_record_context(db, [record])
    report_map = ctx["reports"].get(record.id, {})
    sections = _sections_payload(record)
    return {
        "record_id": record.id,
        "status": record.status,
        "ai_requested": bool(sections.get("_ai_requested")),
        "ai_enhancement_status": _ai_status_from_sections(sections),
        "ai_enhancement_error": str(sections.get("_ai_enhancement_error") or ""),
        "total_score": record.total_score,
        "analysis_mode": record.analysis_mode,
        "analysis_mode_label": public_analysis_mode_label(record.analysis_mode, sections),
        "error_message": record.error_message or "",
        "filename": record.original_filename,
        "target_position": record.target_position or "",
        "reports_ready": record.status == "success" or bool(report_map),
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def record_to_response(
    record: AnalysisRecord,
    include_detail: bool,
    db: Session,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recover_stale_ai_enhancement(record, db)
    if ctx is None:
        ctx = prefetch_record_context(db, [record])
    report_map = ctx["reports"].get(record.id, {})
    source_file = ctx["sources"].get(record.id)
    job_profile = ctx["profiles"].get(record.job_profile_id) if record.job_profile_id else None
    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    raw_sections_payload = dict(sections_payload)
    parse_quality = sections_payload.pop("_parse_quality", "medium")
    parse_warnings = sections_payload.pop("_parse_warnings", [])
    score_reliability = sections_payload.pop("_score_reliability", "normal")
    ai_skip_reason = sections_payload.pop("_ai_skip_reason", "")
    ai_requested = bool(sections_payload.pop("_ai_requested", False))
    ai_enhancement_status = _ai_status_from_sections(sections_payload)
    ai_enhancement_error = str(sections_payload.pop("_ai_enhancement_error", "") or "")
    sections_payload.pop("_ai_enhancement_status", None)
    sections_payload.pop("_ai_enhancement_started_at", None)
    sections_payload.pop("_ai_enhancement_attempts", None)
    sections_payload.pop("_blocks", None)
    structured_suggestions = sections_payload.pop("_structured_suggestions", [])
    weight_template = sections_payload.pop("_weight_template", "default")
    rewrite_preview = sections_payload.pop("_rewrite_preview", {})
    interview_prep = sections_payload.pop("_interview_prep", {})
    mock_interview = sections_payload.pop("_mock_interview", {})
    template_recommendations = sections_payload.pop("_template_recommendations", {})
    parse_entities = sections_payload.pop("_entities", {})
    missing_sections = sections_payload.pop("_missing_sections", [])
    action_roadmap = sections_payload.pop("_action_roadmap", [])
    data: dict[str, Any] = {
        "record_id": record.id,
        "filename": record.original_filename,
        "target_position": record.target_position,
        "job_profile": job_profile_payload(job_profile) if job_profile else None,
        "total_score": record.total_score,
        "analysis_mode": record.analysis_mode,
        "analysis_mode_label": public_analysis_mode_label(
            record.analysis_mode,
            raw_sections_payload,
            ai_requested=ai_requested,
            ai_enhancement_status=ai_enhancement_status,
        ),
        "ai_fallback_reason": "" if ai_requested else (record.error_message or ""),
        "ai_requested": ai_requested,
        "ai_enhancement_status": ai_enhancement_status,
        "ai_enhancement_error": ai_enhancement_error,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "version_no": int(record.version_no or 1),
        "root_record_id": record.root_record_id or record.id,
        "parent_record_id": record.parent_record_id,
        "reports": report_map,
        "reports_on_demand": record.status == "success",
        "source_resume_url": f"/api/resumes/{record.id}/source" if source_file else "",
        "parse_quality": parse_quality,
        "parse_warnings": parse_warnings if isinstance(parse_warnings, list) else [],
        "score_reliability": score_reliability,
        "ai_skip_reason": ai_skip_reason or "",
        "weight_template": weight_template if include_detail else None,
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
                "parse_entities": parse_entities if isinstance(parse_entities, dict) else {},
                "missing_sections": missing_sections if isinstance(missing_sections, list) else [],
                "action_roadmap": action_roadmap if isinstance(action_roadmap, list) else [],
                "match_rate": match_result.get("match_rate"),
                "diagnosis": loads(record.diagnosis_json, []),
                "suggestions": loads(record.suggestions_json, []),
                "structured_suggestions": structured_suggestions if isinstance(structured_suggestions, list) else [],
                "rewrite_preview": rewrite_preview if isinstance(rewrite_preview, dict) else {},
                "interview_prep": interview_prep if isinstance(interview_prep, dict) else {},
                "mock_interview": mock_interview if isinstance(mock_interview, dict) else {},
                "template_recommendations": template_recommendations if isinstance(template_recommendations, dict) else {},
                "match_result": match_result,
                "evidence_snippets": match_result.get("evidence_snippets", []),
                "matched_keywords": match_result.get("matched_keywords", []),
                "missing_keywords": match_result.get("missing_keywords", []),
                "match_confidence": match_result.get("confidence", 0),
                "target_position_source": match_result.get("target_source", "generic"),
                "chart_data": {
                    "bar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
                    "radar": [{"name": label_for_score(key), "value": value} for key, value in scores.items()],
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
            "name": label_for_score(key) if key in WEIGHTS else key,
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


def list_task_center(actor: ActorContext, db: Session) -> dict[str, Any]:
    batch_rows = scope_batches(db.query(BatchTask), actor).order_by(BatchTask.created_at.desc()).limit(100).all()
    single_rows = (
        scope_records(db.query(AnalysisRecord), actor)
        .filter(AnalysisRecord.batch_task_id.is_(None))
        .order_by(AnalysisRecord.created_at.desc())
        .limit(100)
        .all()
    )
    profile_ids = {row.job_profile_id for row in batch_rows + single_rows if row.job_profile_id}
    profiles = prefetch_job_profiles(db, profile_ids)
    batch_items = [
        {
            "task_key": f"batch-{item.id}",
            "task_type": "batch_analysis",
            "task_type_label": "鎵归噺鍒嗘瀽",
            "batch_task_id": item.id,
            "record_id": None,
            "status": item.status,
            "status_label": batch_status_label(item.status),
            "filename": item.zip_filename,
            "target_position": "",
            "total_score": None,
            "processed_files": int(item.success_count or 0) + int(item.failed_count or 0) + int(getattr(item, "skipped_count", 0) or 0),
            "total_files": item.total_files + int(getattr(item, "skipped_count", 0) or 0),
            "success_count": item.success_count,
            "failed_count": item.failed_count,
            "skipped_count": int(getattr(item, "skipped_count", 0) or 0),
            "job_profile": job_profile_payload(profiles[item.job_profile_id]) if item.job_profile_id in profiles else None,
            "created_at": item.created_at.isoformat() if item.created_at else "",
        }
        for item in batch_rows
    ]
    single_items = [
        {
            "task_key": f"record-{item.id}",
            "task_type": "single_analysis",
            "task_type_label": "鍗曚唤鍒嗘瀽",
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
            "job_profile": job_profile_payload(profiles[item.job_profile_id]) if item.job_profile_id in profiles else None,
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
    ctx = prefetch_record_context(db, records)
    items: list[dict[str, Any]] = []
    for record in records:
        report_map = ctx["reports"].get(record.id, {})
        if not report_map and record.status != "success":
            continue
        profile = ctx["profiles"].get(record.job_profile_id) if record.job_profile_id else None
        source_file = ctx["sources"].get(record.id)
        on_demand = record.status == "success"
        sections = _sections_payload(record)
        items.append(
            {
                "record_id": record.id,
                "filename": record.original_filename,
                "target_position": record.target_position,
                "job_profile": job_profile_payload(profile) if profile else None,
                "total_score": record.total_score,
                "analysis_mode": record.analysis_mode,
                "analysis_mode_label": public_analysis_mode_label(record.analysis_mode, sections),
                "status": record.status,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "reports": report_map,
                "reports_on_demand": on_demand,
                "available_formats": sorted(report_map.keys()) if report_map else (["docx", "pdf"] if on_demand else []),
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


def import_guest_records(request: Request, db: Session) -> dict[str, int]:
    user = require_login(request, db)
    guest = default_user(db)
    if user.id == guest.id:
        raise HTTPException(status_code=400, detail="娓稿妯″紡涓嶈兘瀵煎叆娓稿鍘嗗彶")
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


def refresh_interview_prep(record: AnalysisRecord, enable_ai: bool, db: Session) -> dict[str, Any]:
    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    match_result = loads(record.match_result_json, {})
    if not isinstance(match_result, dict):
        match_result = {}
    diagnosis = loads(record.diagnosis_json, [])
    if not isinstance(diagnosis, list):
        diagnosis = []
    sections = {key: value for key, value in sections_payload.items() if not str(key).startswith("_")}
    try:
        interview_prep = build_interview_prep(
            sections,
            match_result,
            diagnosis,
            record.target_position,
            enable_ai=enable_ai,
            raise_on_ai_failure=enable_ai,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sections_payload["_interview_prep"] = interview_prep
    sections_payload["_mock_interview"] = build_mock_interview_session(interview_prep)
    record.sections_json = dumps(sections_payload)
    db.commit()
    return {
        "interview_prep": interview_prep,
        "mock_interview": sections_payload["_mock_interview"],
    }


def refresh_rewrite_preview(record: AnalysisRecord, enable_ai: bool, db: Session) -> dict[str, Any]:
    from app.services.resume_rewriter import build_rewrite_preview, enhance_rewrite_with_ai
    from app.services.resume_template_engine import recommend_resume_templates
    from app.services.score_engine import build_evidence

    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    match_result = loads(record.match_result_json, {})
    if not isinstance(match_result, dict):
        match_result = {}
    sections = {key: value for key, value in sections_payload.items() if not str(key).startswith("_")}
    text = "\n".join(
        line for values in sections.values() if isinstance(values, list) for line in values if str(line).strip()
    )
    evidence = build_evidence(sections, text)
    rewrite_preview = build_rewrite_preview(sections, match_result, evidence, record.target_position)
    if enable_ai:
        try:
            enhanced = enhance_rewrite_with_ai(
                rewrite_preview,
                sections,
                match_result,
                record.target_position,
                text,
                raise_on_failure=True,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if enhanced:
            rewrite_preview = enhanced
    template_recommendations = recommend_resume_templates(
        record.target_position,
        sections_payload.get("_weight_template", "default"),
        sections,
        match_result.get("missing_keywords") or [],
    )
    sections_payload["_rewrite_preview"] = rewrite_preview
    sections_payload["_template_recommendations"] = template_recommendations
    record.sections_json = dumps(sections_payload)
    db.commit()
    return {
        "rewrite_preview": rewrite_preview,
        "template_recommendations": template_recommendations,
    }


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


def download_rewrite_report_file(record_id: int, request: Request, db: Session) -> FileResponse:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="分析未完成，暂无法导出优化稿。")
    sections = loads(record.sections_json, {})
    preview = sections.get("_rewrite_preview") if isinstance(sections, dict) else {}
    if not isinstance(preview, dict) or not preview.get("items"):
        raise HTTPException(status_code=400, detail="当前记录没有可用的改写预览。")
    path = generate_rewrite_report(record.id, record.original_filename, preview)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"rewrite_{record.id}.docx",
    )


def download_report_file(report_id: int, request: Request, format: str, db: Session) -> FileResponse:
    actor = resolve_actor(request, db)
    report = db.query(Report).filter(Report.id == report_id, Report.format == format).first()
    if not report or report.user_id != actor.user.id:
        raise HTTPException(status_code=404, detail="报告不存在。")
    if actor.is_guest and report.guest_session_id != actor.guest_session_id:
        raise HTTPException(status_code=404, detail="报告不存在。")
    path = Path(report.stored_path)
    if not path.exists():
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == report.analysis_record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="报告文件不存在。")
        path = ensure_report_file(record, format)
        report.stored_path = str(path)
        db.commit()
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media_type, filename=path.name)


def download_record_report_file(record_id: int, request: Request, format: str, db: Session) -> FileResponse:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="分析未完成，暂无法导出报告。")
    fmt = format if format in {"docx", "pdf"} else "pdf"
    report = (
        db.query(Report)
        .filter(Report.analysis_record_id == record.id, Report.format == fmt)
        .order_by(Report.id.desc())
        .first()
    )
    path = ensure_report_file(record, fmt)
    if report:
        report.stored_path = str(path)
    else:
        db.add(
            Report(
                user_id=record.user_id,
                guest_session_id=record.guest_session_id,
                analysis_record_id=record.id,
                batch_task_id=record.batch_task_id,
                report_type="single",
                format=fmt,
                stored_path=str(path),
            )
        )
    db.commit()
    media_type = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media_type, filename=path.name)
