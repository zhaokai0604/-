from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.actor import actor_guest_session_value, batch_owned_by_actor, record_owned_by_actor, resolve_actor, scope_batches, scope_records
from app.api.platform import (
    analyze_path,
    batch_to_response,
    get_source_resume_file,
    build_version_compare,
    list_record_versions,
    record_to_response,
    resolve_job_inputs,
    resolve_job_profile,
    resume_media_type,
)
from app.api.schemas import BulkDeleteHistoryRequest
from app.api.task_dispatch import dispatch_batch_task
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import AnalysisRecord, BatchTask, UploadedFile
from app.services.storage import save_upload, validate_upload
from app.tasks.celery_app import celery_enabled
from app.utils.json_tools import dumps

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
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
    if redis_status == "error":
        overall = "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "worker": worker_status,
        "mode": "ai_first",
        "fallback": "offline_rules",
    }


@router.post("/resumes/analyze")
async def analyze_single(
    request: Request,
    file: UploadFile = File(...),
    target_position: str = Form(""),
    job_description: str = Form(""),
    job_profile_id: int = Form(0),
    enable_ai: bool = Form(True),
    parent_record_id: int = Form(0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    content = await file.read()
    validate_upload(file.filename or "", len(content), allow_zip=False)
    await file.seek(0)
    stored_path = await save_upload(file)
    actor = resolve_actor(request, db)
    parent_id = parent_record_id if parent_record_id > 0 else None
    if parent_id:
        parent = db.query(AnalysisRecord).filter(AnalysisRecord.id == parent_id).first()
        if not parent or not record_owned_by_actor(parent, actor):
            raise HTTPException(status_code=404, detail="父版本记录不存在。")
    try:
        return analyze_path(
            db,
            actor.user,
            stored_path,
            file.filename or stored_path.name,
            target_position,
            job_description,
            enable_ai,
            job_profile_id=job_profile_id,
            guest_session_id=actor_guest_session_value(actor),
            parent_record_id=parent_id,
        )
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
    enable_ai: bool = Form(True),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    content = await file.read()
    validate_upload(file.filename or "", len(content), allow_zip=True)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="批量分析只接受 .zip 文件。")
    actor = resolve_actor(request, db)
    existing_batch = (
        scope_batches(db.query(BatchTask), actor)
        .filter(BatchTask.status.in_(["pending", "processing"]))
        .order_by(BatchTask.created_at.desc())
        .first()
    )
    if existing_batch:
        return batch_to_response(existing_batch, include_results=True, db=db)
    await file.seek(0)
    zip_path = await save_upload(file)
    resolved_profile = resolve_job_profile(db, actor, job_profile_id)
    normalized_target_position, normalized_job_description = resolve_job_inputs(target_position, job_description, resolved_profile)
    guest_session_id = actor_guest_session_value(actor)
    batch = BatchTask(
        user_id=actor.user.id,
        guest_session_id=guest_session_id,
        job_profile_id=resolved_profile.id if resolved_profile else None,
        zip_filename=file.filename or zip_path.name,
        status="processing",
        summary_json=dumps([]),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    db.add(
        UploadedFile(
            user_id=actor.user.id,
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


@router.get("/batch-tasks/{batch_task_id}")
def batch_task_detail(batch_task_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    batch = db.query(BatchTask).filter(BatchTask.id == batch_task_id).first()
    if not batch or not batch_owned_by_actor(batch, actor):
        raise HTTPException(status_code=404, detail="批量任务不存在。")
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
def history(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    actor = resolve_actor(request, db)
    records = scope_records(db.query(AnalysisRecord), actor).order_by(AnalysisRecord.created_at.desc()).all()
    return [record_to_response(record, include_detail=False, db=db) for record in records]


@router.post("/history/bulk-delete")
def bulk_delete_history(payload: BulkDeleteHistoryRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.platform import delete_record_with_files

    actor = resolve_actor(request, db)
    if payload.delete_all:
        records = scope_records(db.query(AnalysisRecord), actor).all()
    else:
        unique_ids = sorted({record_id for record_id in payload.record_ids if record_id > 0})
        if not unique_ids:
            raise HTTPException(status_code=400, detail="record_ids cannot be empty when delete_all is false")
        records = scope_records(db.query(AnalysisRecord), actor).filter(AnalysisRecord.id.in_(unique_ids)).all()
    deleted_record_ids = [delete_record_with_files(db, record) for record in records]
    db.commit()
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
    path = Path(source_file.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="原始简历文件不存在。")
    media_type = resume_media_type(path.suffix.lower())
    return FileResponse(path, media_type=media_type, filename=path.name, content_disposition_type="inline")
