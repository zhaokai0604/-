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
    task_type_label,
    user_payload,
)
from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, BatchTask, JobProfile, Report, UploadedFile, User
from app.services.analysis_pipeline import resolve_job_inputs as _resolve_job_inputs, run_analysis_pipeline
from app.services.ai import enhance_with_deepseek
from app.services.batch_service import batch_to_response, process_batch_task, retry_batch_processing
from app.services.interview_engine import build_interview_prep, build_mock_interview_session, collect_question_texts
from app.services.report import (
    ensure_report_file,
    generate_reports,
    generate_rewrite_report,
    report_download_name,
    rewrite_download_name,
)
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
    "apply_pipeline_result_to_record",
    "audit_log_payload",
    "auth_response",
    "batch_status_label",
    "task_type_label",
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


def _repair_legacy_detected_target(record: AnalysisRecord, db: Session) -> None:
    """Repair records created before the no-target auto-adoption guard existed.

    Only records with no saved JD and an explicit ``detected`` source qualify.
    Manual target records are never rewritten. This is a metadata migration only:
    historical scores and diagnostic results are immutable once persisted.

    The old implementation re-ran the full pipeline while serializing a history
    response. That made the first response show the stored score and a refresh
    show a newly calculated score. It also made a read operation dependent on
    the current parser, rules, model, and job library. None of those should
    change an already completed analysis.
    """
    if record.status != "success" or (record.job_description or "").strip():
        return
    sections = _sections_payload(record)
    if sections.get("_legacy_target_repaired"):
        return
    match_result = loads(record.match_result_json, {})
    if not isinstance(match_result, dict) or match_result.get("target_source") != "detected":
        return

    # Keep the existing match payload as evidence/history, but remove the
    # inferred target metadata and target-specific evidence from the public
    # interpretation. In particular, do not touch score fields here.
    repaired_match = dict(match_result)
    repaired_match.update(
        {
            "target_position": "",
            "target_source": "generic",
            "profile": "generic",
            "matched_keywords": [],
            "missing_keywords": [],
            "critical_gaps": [],
            "minor_gaps": [],
            "focus_suggestions": [],
            "summary": "未指定目标岗位，当前结果仅代表通用简历分析。",
        }
    )
    sections["_legacy_target_repaired"] = True
    sections["_legacy_target_repair_note"] = "历史记录曾误采用推断岗位；本次仅修正岗位元数据，保留原有评分结果。"
    sections["_rewrite_preview"] = {
        **(sections.get("_rewrite_preview") or {}),
        "target_position": "目标岗位",
        "summary": "未指定目标岗位，以下为通用简历优化参考。",
    }
    sections["_template_recommendations"] = {
        **(sections.get("_template_recommendations") or {}),
        "target_position": "通用",
        "summary": "未指定目标岗位，推荐通用简历结构参考。",
    }
    warnings = sections.get("_quality_warnings")
    if not isinstance(warnings, list):
        warnings = []
    warning = "历史记录未指定目标岗位，岗位匹配结果已降级为通用解释；原有评分未重算。"
    if warning not in warnings:
        warnings.append(warning)
    sections["_quality_warnings"] = warnings
    record.target_position = ""
    record.job_profile_id = None
    record.match_result_json = dumps(repaired_match)
    record.sections_json = dumps(sections)
    db.commit()
    db.refresh(record)


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
    *,
    target_match_enabled: bool = False,
    stream: bool = False,
) -> AnalysisRecord:
    # 岗位是否参与分析必须由请求开关决定，不能由残留字符串或模板 ID 反推。
    target_match_enabled = bool(target_match_enabled)
    profile = (
        resolve_job_profile(db, ActorContext(user=user, guest_session_id=guest_session_id), job_profile_id)
        if target_match_enabled
        else None
    )
    if target_match_enabled:
        target_position, job_description = resolve_job_inputs(target_position, job_description, profile)
    else:
        target_position, job_description, job_profile_id = "", "", 0
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
        sections_json=dumps(
            {
                "_job": {
                    "enable_ai": enable_ai,
                    "stream": bool(stream),
                    "target_match_enabled": target_match_enabled,
                }
            }
        ),
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


def apply_pipeline_result_to_record(db: Session, record: AnalysisRecord, pipeline: dict[str, Any]) -> None:
    """将 pipeline 结果写入分析记录并置为 success（流式落库与后台任务共用）。"""
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


def process_single_analysis(record_id: int) -> None:
    with SessionLocal() as db:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
        if not record or record.status != "processing":
            return
        job_meta = loads(record.sections_json, {}).get("_job", {})
        if not isinstance(job_meta, dict):
            job_meta = {}
        target_match_enabled = bool(job_meta.get("target_match_enabled", False))
        # stream 任务优先交给 analysis-live；短暂等待认领，超时则后台兜底
        if job_meta.get("stream"):
            import time

            for _ in range(24):
                db.refresh(record)
                if record.status != "processing":
                    return
                meta = loads(record.sections_json, {}).get("_job", {})
                if isinstance(meta, dict) and meta.get("live_claimed"):
                    return
                time.sleep(0.5)
            job_meta = loads(record.sections_json, {}).get("_job", {})
            if not isinstance(job_meta, dict):
                job_meta = {}
            if job_meta.get("live_claimed"):
                return
        upload = get_source_resume_file(db, record.id, record.user_id)
        if not upload or not Path(upload.stored_path).exists():
            record.status = "failed"
            record.error_message = "找不到原始简历文件。"
            db.commit()
            return
        path = Path(upload.stored_path)
        enable_ai = bool(job_meta.get("enable_ai", True))
        profile = (
            db.query(JobProfile).filter(JobProfile.id == record.job_profile_id).first()
            if target_match_enabled and record.job_profile_id
            else None
        )
        target_position = record.target_position if target_match_enabled else ""
        job_description = record.job_description if target_match_enabled else ""
        try:
            pipeline = _run_analysis_pipeline(path, target_position, job_description, enable_ai, profile)
            apply_pipeline_result_to_record(db, record, pipeline)
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
                 "layout_complexity": sections_payload.get("_layout_complexity", 0.0),
                 "evidence_coverage": sections_payload.get("_evidence_coverage", 0.0),
                 "quality_warnings": sections_payload.get("_quality_warnings", []),
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
    job_meta = sections.get("_job") if isinstance(sections.get("_job"), dict) else {}
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
        "target_match_enabled": bool(job_meta.get("target_match_enabled", bool(record.target_position or record.job_description))),
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
    _repair_legacy_detected_target(record, db)
    if ctx is None:
        ctx = prefetch_record_context(db, [record])
    report_map = ctx["reports"].get(record.id, {})
    source_file = ctx["sources"].get(record.id)
    job_profile = ctx["profiles"].get(record.job_profile_id) if record.job_profile_id else None
    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    raw_sections_payload = dict(sections_payload)
    job_meta = raw_sections_payload.get("_job") if isinstance(raw_sections_payload.get("_job"), dict) else {}
    parse_quality = sections_payload.pop("_parse_quality", "medium")
    parse_warnings = sections_payload.pop("_parse_warnings", [])
    score_reliability = sections_payload.pop("_score_reliability", "normal")
    layout_complexity = sections_payload.pop("_layout_complexity", 0.0)
    evidence_coverage = sections_payload.pop("_evidence_coverage", 0.0)
    quality_warnings = sections_payload.pop("_quality_warnings", [])
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
    skill_graph = sections_payload.pop("_skill_graph", {})
    low_snr_zones = sections_payload.pop("_low_snr_zones", [])
    evidence_confidence = sections_payload.pop("_evidence_confidence", None)
    low_snr_penalty = sections_payload.pop("_low_snr_penalty", {})
    interview_prep = sections_payload.pop("_interview_prep", {})
    mock_interview = sections_payload.pop("_mock_interview", {})
    template_recommendations = sections_payload.pop("_template_recommendations", {})
    parse_entities = sections_payload.pop("_entities", {})
    structured_profile = sections_payload.pop("_structured", None)
    if not isinstance(structured_profile, dict) and isinstance(parse_entities, dict):
        maybe = parse_entities.get("structured")
        structured_profile = maybe if isinstance(maybe, dict) else {}
    missing_sections = sections_payload.pop("_missing_sections", [])
    action_roadmap = sections_payload.pop("_action_roadmap", [])
    job_market_match = sections_payload.pop("_job_market_match", {})
    data: dict[str, Any] = {
        "record_id": record.id,
        "filename": record.original_filename,
        "target_position": record.target_position,
        "target_match_enabled": bool(job_meta.get("target_match_enabled", bool(record.target_position or record.job_description))),
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
         "layout_complexity": layout_complexity,
         "evidence_coverage": evidence_coverage,
         "quality_warnings": quality_warnings if isinstance(quality_warnings, list) else [],
        "ai_skip_reason": ai_skip_reason or "",
        "weight_template": weight_template if include_detail else None,
        "job_market_match": job_market_match if isinstance(job_market_match, dict) else {},
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
                "structured": structured_profile if isinstance(structured_profile, dict) else {},
                "missing_sections": missing_sections if isinstance(missing_sections, list) else [],
                "action_roadmap": action_roadmap if isinstance(action_roadmap, list) else [],
                "match_rate": match_result.get("match_rate"),
                "diagnosis": loads(record.diagnosis_json, []),
                "suggestions": loads(record.suggestions_json, []),
                "structured_suggestions": structured_suggestions if isinstance(structured_suggestions, list) else [],
                "rewrite_preview": rewrite_preview if isinstance(rewrite_preview, dict) else {},
                "skill_graph": skill_graph if isinstance(skill_graph, dict) else {},
                "low_snr_zones": low_snr_zones if isinstance(low_snr_zones, list) else [],
                 "evidence_confidence": evidence_confidence,
                 "layout_complexity": layout_complexity,
                 "evidence_coverage": evidence_coverage,
                 "quality_warnings": quality_warnings if isinstance(quality_warnings, list) else [],
                "low_snr_penalty": low_snr_penalty if isinstance(low_snr_penalty, dict) else {},
                "interview_prep": interview_prep if isinstance(interview_prep, dict) else {},
                "mock_interview": mock_interview if isinstance(mock_interview, dict) else {},
                "template_recommendations": template_recommendations if isinstance(template_recommendations, dict) else {},
                "match_result": match_result,
                "evidence_snippets": match_result.get("evidence_snippets", []),
                "matched_keywords": match_result.get("matched_keywords", []),
                "missing_keywords": match_result.get("missing_keywords", []),
                "critical_gaps": match_result.get("critical_gaps", []),
                "minor_gaps": match_result.get("minor_gaps", []),
                "ats_breakdown": match_result.get("ats_breakdown", {}),
                "match_confidence": match_result.get("confidence", 0),
                "rule_score": match_result.get("rule_score"),
                "semantic_score": match_result.get("semantic_score"),
                "match_backend": match_result.get("match_backend"),
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
    dimension_deltas = []
    for key in keys:
        a_val = float(scores_a.get(key, 0) or 0)
        b_val = float(scores_b.get(key, 0) or 0)
        delta = round(b_val - a_val, 1)
        dimension_deltas.append(
            {
                "name": label_for_score(key) if key in WEIGHTS else key,
                "key": key,
                "a": a_val,
                "b": b_val,
                "delta": delta,
                "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
            }
        )
    total_a = float(record_a.total_score or 0)
    total_b = float(record_b.total_score or 0)
    total_delta = round(total_b - total_a, 1)

    # 附带优化稿改动数，便于时光机展示「改了多少」
    sections_a = loads(record_a.sections_json, {})
    sections_b = loads(record_b.sections_json, {})
    rewrite_a = sections_a.get("_rewrite_preview") if isinstance(sections_a, dict) else {}
    rewrite_b = sections_b.get("_rewrite_preview") if isinstance(sections_b, dict) else {}
    opt_a = rewrite_a.get("optimized_resume") if isinstance(rewrite_a, dict) else {}
    opt_b = rewrite_b.get("optimized_resume") if isinstance(rewrite_b, dict) else {}

    return {
        "a": {
            "record_id": record_a.id,
            "version_no": int(record_a.version_no or 1),
            "filename": record_a.original_filename,
            "total_score": total_a,
            "created_at": record_a.created_at.isoformat() if record_a.created_at else "",
            "optimized_change_count": int((opt_a or {}).get("change_count") or 0),
        },
        "b": {
            "record_id": record_b.id,
            "version_no": int(record_b.version_no or 1),
            "filename": record_b.original_filename,
            "total_score": total_b,
            "created_at": record_b.created_at.isoformat() if record_b.created_at else "",
            "optimized_change_count": int((opt_b or {}).get("change_count") or 0),
        },
        "summary": {
            "total_score_delta": total_delta,
            "improved": total_b > total_a,
            "unchanged": total_b == total_a,
            "direction": "up" if total_delta > 0 else "down" if total_delta < 0 else "flat",
            "improved_dimensions": sum(1 for item in dimension_deltas if item["delta"] > 0),
            "declined_dimensions": sum(1 for item in dimension_deltas if item["delta"] < 0),
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
            "task_type_label": task_type_label("batch_analysis"),
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
            "task_type_label": task_type_label("single_analysis"),
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
    previous_questions = collect_question_texts(sections_payload.get("_interview_prep"))
    previous_questions.extend(collect_question_texts(sections_payload.get("_mock_interview")))
    try:
        interview_prep = build_interview_prep(
            sections,
            match_result,
            diagnosis,
            record.target_position,
            enable_ai=enable_ai,
            raise_on_ai_failure=enable_ai,
            exclude_questions=previous_questions,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sections_payload["_interview_prep"] = interview_prep
    sections_payload["_mock_interview"] = build_mock_interview_session(
        interview_prep,
        exclude_questions=previous_questions,
    )
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
    from app.services.optimized_resume import attach_optimized_resume
    from app.services.skill_graph import build_skill_graph_hints

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
    skill_graph = build_skill_graph_hints(
        text,
        match_result.get("matched_keywords") or [],
        match_result.get("missing_keywords") or [],
        record.target_position or "",
    )
    rewrite_preview = attach_optimized_resume(
        rewrite_preview,
        sections,
        skill_hints=skill_graph.get("hints") or [],
    )
    template_recommendations = recommend_resume_templates(
        record.target_position,
        sections_payload.get("_weight_template", "default"),
        sections,
        match_result.get("missing_keywords") or [],
    )
    sections_payload["_rewrite_preview"] = rewrite_preview
    sections_payload["_skill_graph"] = skill_graph
    sections_payload["_template_recommendations"] = template_recommendations
    record.sections_json = dumps(sections_payload)
    db.commit()
    return {
        "rewrite_preview": rewrite_preview,
        "skill_graph": skill_graph,
        "template_recommendations": template_recommendations,
    }


def apply_recommended_job(
    record: AnalysisRecord,
    db: Session,
    *,
    job_id: str = "",
    source_url: str = "",
    target_position: str = "",
) -> dict[str, Any]:
    """Re-score an existing analysis against a user-selected related job."""
    from app.services.job_market import find_verified_job, select_job_for_resume
    from app.services.job_market import _build_requirement_basis as build_requirement_basis
    from app.services.job_market import _record_description as record_description
    from app.services.optimized_resume import attach_optimized_resume
    from app.services.resume_rewriter import build_rewrite_preview
    from app.services.resume_template_engine import recommend_resume_templates
    from app.services.score_engine import build_evidence
    from app.services.scoring import analyze_resume
    from app.services.skill_graph import build_skill_graph_hints
    from app.services.suggestion_engine import build_action_roadmap

    job = find_verified_job(job_id=job_id, source_url=source_url, target_position=target_position)
    if not job:
        raise HTTPException(status_code=404, detail="未找到对应的公开岗位，请从推荐列表重新选择。")

    sections_payload = loads(record.sections_json, {})
    if not isinstance(sections_payload, dict):
        sections_payload = {}
    sections = {key: value for key, value in sections_payload.items() if not str(key).startswith("_")}
    text = "\n".join(
        line for values in sections.values() if isinstance(values, list) for line in values if str(line).strip()
    )
    if not text.strip():
        raise HTTPException(status_code=400, detail="当前记录缺少可分析正文，无法切换岗位。")

    previous_market = sections_payload.get("_job_market_match")
    previous_related = []
    if isinstance(previous_market, dict):
        previous_related = list(previous_market.get("related_jobs") or [])

    position = str(job.get("target_position") or target_position or "").strip()
    description = record_description(job)
    market_match = select_job_for_resume(text, sections, position, description)
    if not market_match.get("matched"):
        # 仍强制按所选岗位评价：用库内 JD 组装证据卡
        matched_kw = list(market_match.get("matched_keywords") or [])
        market_match = {
            **market_match,
            "matched": True,
            "fallback_used": False,
            "recommendation_only": False,
            "adopted_as_target": True,
            "id": job.get("id", ""),
            "target_position": position,
            "job_description": description,
            "company": job.get("company", ""),
            "city": job.get("city", ""),
            "category": job.get("category", ""),
            "source_url": job.get("source_url", ""),
            "source_type": job.get("source_type", "public_job_page"),
            "review_status": job.get("review_status", "single_source_verified"),
            "requirement_basis": build_requirement_basis(job, matched_kw),
            "quality_warning": "已按您点选的公开岗位重新评价。",
        }
    else:
        market_match = {
            **market_match,
            "adopted_as_target": True,
            "recommendation_only": False,
            "id": job.get("id", "") or market_match.get("id", ""),
            "quality_warning": "已按您点选的公开岗位重新评价。",
        }
    if previous_related:
        market_match["related_jobs"] = previous_related

    parsed = {
        "sections": sections,
        "raw_text": text,
        "parse_quality": sections_payload.get("_parse_quality", "medium"),
        "parse_warnings": sections_payload.get("_parse_warnings", []),
        "layout_complexity": sections_payload.get("_layout_complexity", 0.0),
        "entities": sections_payload.get("_entities", {}),
        "structured": sections_payload.get("_structured", {}),
        "missing_sections": sections_payload.get("_missing_sections", []),
        "job_market_match": market_match,
    }
    result = analyze_resume(
        parsed,
        position,
        description,
        target_source_override="selected",
        allow_detected=False,
    )
    result["job_market_match"] = market_match
    match_result = result.get("match_result", {}) if isinstance(result.get("match_result"), dict) else {}
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    rewrite_preview = build_rewrite_preview(sections, match_result, evidence, position)
    skill_graph = build_skill_graph_hints(
        text,
        match_result.get("matched_keywords") or [],
        match_result.get("missing_keywords") or [],
        position,
    )
    rewrite_preview = attach_optimized_resume(
        rewrite_preview,
        sections,
        skill_hints=skill_graph.get("hints") or [],
    )
    template_recommendations = recommend_resume_templates(
        position,
        result.get("weight_template", sections_payload.get("_weight_template", "default")),
        sections,
        match_result.get("missing_keywords") or [],
    )
    action_roadmap = build_action_roadmap(
        result.get("scores", {}),
        result.get("structured_suggestions", []),
        match_result,
        str(result.get("parse_quality", sections_payload.get("_parse_quality", "medium"))),
        sections_payload.get("_missing_sections", []),
        result.get("diagnosis", []),
    )

    sections_payload["_job_market_match"] = market_match
    sections_payload["_rewrite_preview"] = rewrite_preview
    sections_payload["_skill_graph"] = skill_graph
    sections_payload["_template_recommendations"] = template_recommendations
    sections_payload["_action_roadmap"] = action_roadmap
    sections_payload["_low_snr_zones"] = result.get("low_snr_zones") or evidence.get("low_snr_zones") or []
    sections_payload["_evidence_confidence"] = result.get("evidence_confidence", evidence.get("evidence_confidence", 0.5))
    sections_payload["_low_snr_penalty"] = result.get("low_snr_penalty") or {}
    sections_payload["_score_reliability"] = result.get("score_reliability", sections_payload.get("_score_reliability", "normal"))
    sections_payload["_evidence_coverage"] = result.get("evidence_coverage", sections_payload.get("_evidence_coverage", 0.0))
    sections_payload["_quality_warnings"] = result.get("quality_warnings", [])
    sections_payload["_parse_quality"] = result.get("parse_quality", sections_payload.get("_parse_quality", "medium"))
    sections_payload["_selected_job_at"] = datetime.utcnow().isoformat() + "Z"

    record.target_position = position
    record.job_description = description
    record.total_score = result["total_score"]
    record.scores_json = dumps(result["scores"])
    record.diagnosis_json = dumps(result["diagnosis"])
    record.suggestions_json = dumps(result["suggestions"])
    record.match_result_json = dumps(result["match_result"])
    record.sections_json = dumps(sections_payload)
    db.commit()
    db.refresh(record)
    return record_to_response(record, include_detail=True, db=db)


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
    has_optimized = isinstance(preview, dict) and isinstance(preview.get("optimized_resume"), dict)
    if not isinstance(preview, dict) or (not preview.get("items") and not has_optimized):
        raise HTTPException(status_code=400, detail="当前记录没有可用的优化稿。")
    path = generate_rewrite_report(record.id, record.original_filename, preview)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=rewrite_download_name(record.original_filename, record.id, record.version_no),
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
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == report.analysis_record_id).first()
    return FileResponse(
        path,
        media_type=media_type,
        filename=report_download_name(
            record.original_filename if record else "简历",
            record.id if record else report.id,
            format,
            record.version_no if record else 1,
        ),
    )


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
    return FileResponse(
        path,
        media_type=media_type,
        filename=report_download_name(record.original_filename, record.id, fmt, record.version_no),
    )
