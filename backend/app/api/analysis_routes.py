import base64
import binascii
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.actor import (
    actor_guest_session_value,
    batch_owned_by_actor,
    record_owned_by_actor,
    resolve_actor,
    scope_batches,
    scope_records,
)
from app.api.platform import (
    batch_to_response,
    build_version_compare,
    create_single_analysis_job,
    get_source_resume_file,
    list_record_versions,
    record_to_response,
    records_to_response,
    resolve_job_inputs,
    resolve_job_profile,
    resume_media_type,
    retry_single_analysis,
)
from app.api.request_limits import enforce_upload_rate_limit
from app.api.schemas import ApplyRecommendedJobRequest, BulkDeleteHistoryRequest, DirectResumeAnalyzeRequest
from app.api.task_dispatch import dispatch_batch_task, dispatch_single_analysis
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import AnalysisRecord, BatchTask, UploadedFile
from app.services.storage import resolve_allowed_data_path, safe_download_filename, save_upload_bytes, validate_upload
from app.tasks.celery_app import celery_enabled
from app.utils.json_tools import dumps

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.get("/resume-templates/catalog")
def resume_template_catalog() -> dict[str, Any]:
    from app.services.resume_template_engine import list_template_catalog

    return {"templates": list_template_catalog()}


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    import shutil

    from sqlalchemy import text

    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "disabled"
    if settings.redis_url:
        try:
            import redis

            client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
            client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"

    worker_status = "celery" if celery_enabled() else "background_tasks"
    overall = "ok" if db_status == "ok" else "degraded"
    if redis_status == "error" and celery_enabled():
        overall = "degraded"

    disk_free_mb = None
    try:
        usage = shutil.disk_usage(settings.data_dir)
        disk_free_mb = round(usage.free / (1024 * 1024), 1)
        if disk_free_mb < 512:
            overall = "degraded"
    except OSError:
        disk_free_mb = None

    return {
        "status": overall,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": db_status,
        "redis": redis_status,
        "worker": worker_status,
        "disk_free_mb": disk_free_mb,
        "mode": "ai_first",
        "fallback": "offline_rules",
    }


@router.post("/resumes/analyze")
async def analyze_single(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    target_position: str = Form(""),
    job_description: str = Form(""),
    job_profile_id: int = Form(0),
    target_match_enabled: bool = Form(False),
    enable_ai: bool = Form(True),
    parent_record_id: int = Form(0),
    stream: bool = Form(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    content = await file.read()
    validate_upload(file.filename or "", len(content), allow_zip=False)
    actor = resolve_actor(request, db)
    enforce_upload_rate_limit(request, actor)
    stored_path = save_upload_bytes(content, file.filename or "")
    logger.info(
        "analysis_request endpoint=upload stream=%s target_match_enabled=%s target_position_present=%s jd_length=%s profile_id=%s",
        bool(stream),
        bool(target_match_enabled),
        bool(target_position.strip()),
        len(job_description.strip()),
        job_profile_id if target_match_enabled else 0,
    )
    parent_id = parent_record_id if parent_record_id > 0 else None
    if parent_id:
        parent = db.query(AnalysisRecord).filter(AnalysisRecord.id == parent_id).first()
        if not parent or not record_owned_by_actor(parent, actor):
            raise HTTPException(status_code=404, detail="父版本记录不存在。")
    try:
        record = create_single_analysis_job(
            db,
            actor.user,
            stored_path,
            file.filename or stored_path.name,
            target_position if target_match_enabled else "",
            job_description if target_match_enabled else "",
            enable_ai,
            job_profile_id=job_profile_id if target_match_enabled else 0,
            guest_session_id=actor_guest_session_value(actor),
            parent_record_id=parent_id,
            target_match_enabled=target_match_enabled,
            stream=stream,
        )
        # stream 时由 analysis-live 优先认领；后台任务等待 live_claimed 超时后再兜底，避免 SSE 断连卡死。
        dispatch_single_analysis(background_tasks, record.id)
        payload = record_to_response(record, include_detail=False, db=db)
        payload["async"] = True
        payload["stream"] = bool(stream)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resumes/analyze-direct")
async def analyze_single_direct(
    payload: DirectResumeAnalyzeRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    encoded = payload.content_base64.strip()
    if encoded.startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="上传文件编码无效。") from exc

    validate_upload(payload.filename or "", len(content), allow_zip=False)
    actor = resolve_actor(request, db)
    enforce_upload_rate_limit(request, actor)
    stored_path = save_upload_bytes(content, payload.filename or "")
    logger.info(
        "analysis_request endpoint=direct stream=%s target_match_enabled=%s target_position_present=%s jd_length=%s profile_id=%s",
        bool(payload.stream),
        bool(payload.target_match_enabled),
        bool(payload.target_position.strip()),
        len(payload.job_description.strip()),
        payload.job_profile_id if payload.target_match_enabled else 0,
    )
    parent_id = payload.parent_record_id if payload.parent_record_id > 0 else None
    if parent_id:
        parent = db.query(AnalysisRecord).filter(AnalysisRecord.id == parent_id).first()
        if not parent or not record_owned_by_actor(parent, actor):
            raise HTTPException(status_code=404, detail="父版本记录不存在。")
    try:
        record = create_single_analysis_job(
            db,
            actor.user,
            stored_path,
            payload.filename or stored_path.name,
            payload.target_position if payload.target_match_enabled else "",
            payload.job_description if payload.target_match_enabled else "",
            payload.enable_ai,
            job_profile_id=payload.job_profile_id if payload.target_match_enabled else 0,
            guest_session_id=actor_guest_session_value(actor),
            parent_record_id=parent_id,
            target_match_enabled=payload.target_match_enabled,
            stream=payload.stream,
        )
        dispatch_single_analysis(background_tasks, record.id)
        response = record_to_response(record, include_detail=False, db=db)
        response["async"] = True
        response["stream"] = bool(payload.stream)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resumes/analyze-zip")
async def analyze_zip(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    target_position: str = Form(""),
    job_description: str = Form(""),
    job_profile_id: int = Form(0),
    target_match_enabled: bool = Form(False),
    enable_ai: bool = Form(True),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    content = await file.read()
    validate_upload(file.filename or "", len(content), allow_zip=True)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="批量分析只接受 .zip 文件。")
    actor = resolve_actor(request, db)
    enforce_upload_rate_limit(request, actor)
    existing_batch = (
        scope_batches(db.query(BatchTask), actor)
        .filter(BatchTask.status.in_(["pending", "processing"]))
        .order_by(BatchTask.created_at.desc())
        .first()
    )
    if existing_batch:
        response = batch_to_response(existing_batch, include_results=True, db=db)
        response["reused"] = True
        return response
    zip_path = save_upload_bytes(content, file.filename or "")
    resolved_profile = resolve_job_profile(db, actor, job_profile_id) if target_match_enabled else None
    if not target_match_enabled:
        target_position = ""
        job_description = ""
    normalized_target_position, normalized_job_description = resolve_job_inputs(target_position, job_description, resolved_profile)
    guest_session_id = actor_guest_session_value(actor)
    batch = BatchTask(
        user_id=actor.user.id,
        organization_id=actor.organization_id,
        guest_session_id=guest_session_id,
        job_profile_id=resolved_profile.id if resolved_profile else None,
        zip_filename=file.filename or zip_path.name,
        status="processing",
        enable_ai=enable_ai,
        summary_json=dumps([]),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    db.add(
        UploadedFile(
            user_id=actor.user.id,
            organization_id=actor.organization_id,
            guest_session_id=guest_session_id,
            batch_task_id=batch.id,
            original_filename=file.filename or zip_path.name,
            stored_path=str(zip_path),
            file_type=zip_path.suffix.lower(),
            file_size=len(content),
        )
    )
    db.commit()
    dispatch_batch_task(
        background_tasks,
        batch_task_id=batch.id,
        user_id=actor.user.id,
        zip_path_str=str(zip_path),
        target_position=normalized_target_position,
        job_description=normalized_job_description,
        enable_ai=enable_ai,
        job_profile_id=resolved_profile.id if resolved_profile else None,
        guest_session_id=guest_session_id,
    )
    return batch_to_response(batch, include_results=True, db=db)


@router.post("/batch-tasks/{batch_task_id}/pause")
def pause_batch_task(batch_task_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    batch = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
    if not batch or not batch_owned_by_actor(batch, actor):
        raise HTTPException(status_code=404, detail="批量任务不存在。")
    if batch.status != "processing":
        raise HTTPException(status_code=400, detail="只有正在处理的批量任务才能暂停。")
    batch.status = "paused"
    db.commit()
    db.refresh(batch)
    return batch_to_response(batch, include_results=True, db=db)


@router.post("/batch-tasks/{batch_task_id}/retry")
def retry_batch_task(
    batch_task_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.api.platform import retry_batch_processing

    actor = resolve_actor(request, db)
    batch = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
    if not batch or not batch_owned_by_actor(batch, actor):
        raise HTTPException(status_code=404, detail="批量任务不存在。")
    if batch.status in {"pending", "processing"}:
        raise HTTPException(status_code=400, detail="任务正在处理中，无需重试。")
    return retry_batch_processing(batch, actor.user, background_tasks, db)


@router.get("/history")
def history(
    request: Request,
    limit: int = 500,
    offset: int = 0,
    include_total: bool = True,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    query = scope_records(db.query(AnalysisRecord), actor).order_by(AnalysisRecord.created_at.desc())
    total = query.count() if include_total else None
    records = query.offset(offset).limit(limit).all()
    payload: dict[str, Any] = {
        "items": records_to_response(records, include_detail=False, db=db),
        "limit": limit,
        "offset": offset,
    }
    if total is not None:
        payload["total"] = total
    return payload


@router.post("/history/bulk-delete")
def bulk_delete_history(payload: BulkDeleteHistoryRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.platform import delete_record_with_files

    actor = resolve_actor(request, db)
    if payload.delete_all:
        records = scope_records(db.query(AnalysisRecord), actor).all()
    else:
        unique_ids = sorted({record_id for record_id in payload.record_ids if record_id > 0})
        if not unique_ids:
            raise HTTPException(status_code=400, detail="请至少选择一条记录，或勾选清空全部。")
        records = scope_records(db.query(AnalysisRecord), actor).filter(AnalysisRecord.id.in_(unique_ids)).all()
    try:
        deleted_record_ids = [delete_record_with_files(db, record) for record in records]
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="批量删除失败，请稍后重试。") from exc
    return {"deleted": True, "deleted_count": len(deleted_record_ids), "deleted_record_ids": deleted_record_ids}


@router.get("/history/compare")
def history_compare(a: int, b: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    if a <= 0 or b <= 0 or a == b:
        raise HTTPException(status_code=400, detail="请选择两个不同的版本记录进行对比。")
    record_a = db.query(AnalysisRecord).filter(AnalysisRecord.id == a).first()
    record_b = db.query(AnalysisRecord).filter(AnalysisRecord.id == b).first()
    if not record_a or not record_b or not record_owned_by_actor(record_a, actor) or not record_owned_by_actor(record_b, actor):
        raise HTTPException(status_code=404, detail="对比记录不存在。")
    root_a = record_a.root_record_id or record_a.id
    root_b = record_b.root_record_id or record_b.id
    if root_a != root_b:
        raise HTTPException(status_code=400, detail="只能对比同一简历版本链中的记录。")
    if record_a.version_no > record_b.version_no:
        record_a, record_b = record_b, record_a
    compare = build_version_compare(record_a, record_b)
    all_versions = list_record_versions(record_a, db)
    compare["trend"] = [
        {
            "version_no": item["version_no"],
            "record_id": item["record_id"],
            "total_score": item["total_score"],
            "created_at": item["created_at"],
        }
        for item in all_versions
    ]
    return compare


@router.post("/history/{record_id}/retry")
def retry_single_analysis_route(
    record_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.batch_task_id:
        raise HTTPException(status_code=400, detail="批量任务请前往批量分析页重试。")
    return retry_single_analysis(record, background_tasks, db)


@router.post("/history/{record_id}/rewrite-preview/refresh")
def refresh_rewrite_preview_route(
    record_id: int,
    request: Request,
    enable_ai: bool = False,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.api.platform import refresh_rewrite_preview

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="仅支持对已完成的分析记录生成改写预览。")
    return refresh_rewrite_preview(record, enable_ai=enable_ai, db=db)


@router.post("/history/{record_id}/interview-prep/refresh")
def refresh_interview_prep_route(
    record_id: int,
    request: Request,
    enable_ai: bool = False,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.api.platform import refresh_interview_prep

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="仅支持对已完成的分析记录生成面试题。")
    interview_prep = refresh_interview_prep(record, enable_ai=enable_ai, db=db)
    return interview_prep


@router.post("/history/{record_id}/apply-job")
def apply_recommended_job_route(
    record_id: int,
    payload: ApplyRecommendedJobRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """将推荐岗位设为分析目标，并重算该岗专属评价与匹配报告。"""
    from app.api.platform import apply_recommended_job

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="仅支持对已完成的分析记录切换岗位。")
    if not (payload.job_id or payload.source_url or payload.target_position):
        raise HTTPException(status_code=400, detail="请指定要应用的推荐岗位。")
    return apply_recommended_job(
        record,
        db,
        job_id=payload.job_id,
        source_url=payload.source_url,
        target_position=payload.target_position,
    )


@router.get("/history/{record_id}/rewrite-report")
def download_rewrite_report(record_id: int, request: Request, db: Session = Depends(get_db)):
    from app.api.platform import download_rewrite_report_file

    return download_rewrite_report_file(record_id, request, db)


@router.get("/history/{record_id}/analysis-stream")
def replay_analysis_stream(record_id: int, request: Request, db: Session = Depends(get_db)):
    """SSE：重放真实分析结果的「实时解析流」（用于演示智能体阅读过程）。"""
    from app.api.platform import record_to_response
    from app.services.analysis_replay import iter_replay_events

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status != "success":
        raise HTTPException(status_code=400, detail="仅支持对已完成的分析重放解析流。")
    payload = record_to_response(record, include_detail=True, db=db)
    return StreamingResponse(
        iter_replay_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{record_id}/analysis-live")
def live_analysis_stream(record_id: int, request: Request, db: Session = Depends(get_db)):
    """SSE：上传后真实跑 pipeline，边推事件边在 done 时落库。"""
    from app.services.analysis_stream import iter_live_analysis_and_persist

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    if record.status not in {"processing", "success"}:
        raise HTTPException(status_code=400, detail="当前状态不支持实时分析流。")
    return StreamingResponse(
        iter_live_analysis_and_persist(record_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/batch-tasks/{batch_task_id}")
def batch_task_detail(
    batch_task_id: int,
    request: Request,
    include_results: bool = True,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    batch = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
    if not batch or not batch_owned_by_actor(batch, actor):
        raise HTTPException(status_code=404, detail="批量任务不存在。")
    return batch_to_response(batch, include_results=include_results, db=db)


@router.get("/history/{record_id}/report/download")
def download_record_report(
    record_id: int,
    request: Request,
    format: str = "pdf",
    db: Session = Depends(get_db),
):
    from app.api.platform import download_record_report_file

    return download_record_report_file(record_id, request, format, db)


@router.get("/history/{record_id}/status")
def history_status(record_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.platform import record_status_response

    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    return record_status_response(record, db)


@router.get("/history/{record_id}")
def history_detail(record_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    return record_to_response(record, include_detail=True, db=db)


@router.get("/history/{record_id}/versions")
def history_versions(record_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    versions = list_record_versions(record, db)
    return {
        "root_record_id": record.root_record_id or record.id,
        "current_record_id": record.id,
        "versions": versions,
        "trend": [
            {
                "version_no": item["version_no"],
                "record_id": item["record_id"],
                "total_score": item["total_score"],
                "created_at": item["created_at"],
            }
            for item in versions
        ],
    }


@router.get("/resumes/{record_id}/source")
def download_source_resume(record_id: int, request: Request, db: Session = Depends(get_db)) -> FileResponse:
    actor = resolve_actor(request, db)
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record or not record_owned_by_actor(record, actor):
        raise HTTPException(status_code=404, detail="记录不存在。")
    source_file = get_source_resume_file(db, record.id, record.user_id)
    if not source_file:
        raise HTTPException(status_code=404, detail="原始简历文件不存在。")
    safe_path = resolve_allowed_data_path(source_file.stored_path)
    media_type = resume_media_type(safe_path.suffix.lower())
    # 原始文件属于用户私有材料：允许下载，但使用用户上传时的文件名，避免暴露服务器 UUID。
    return FileResponse(
        safe_path,
        media_type=media_type,
        filename=safe_download_filename(source_file.original_filename, safe_path.name),
        content_disposition_type="attachment",
    )
