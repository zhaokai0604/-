"""批量任务：ZIP 解压、逐份分析、进度同步与重试。"""

from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.serializers import batch_status_label, job_profile_payload, public_analysis_mode_label
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, BatchTask, JobProfile, UploadedFile, User
from app.services.zip_service import safe_extract_zip
from app.utils.json_tools import dumps, loads

BATCH_PROGRESS_COMMIT_INTERVAL = 3


def _analyze_batch_file(
    path: Path,
    *,
    user_id: int,
    batch_task_id: int,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    job_profile_id: int,
    guest_session_id: str | None,
) -> dict[str, Any]:
    from app.api.platform import analyze_path

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise RuntimeError("批量分析用户不存在。")
        return analyze_path(
            db,
            user,
            path,
            path.name,
            target_position,
            job_description,
            enable_ai,
            batch_task_id,
            job_profile_id or 0,
            guest_session_id=guest_session_id,
        )


def batch_to_response(batch: BatchTask, include_results: bool, db: Session) -> dict[str, Any]:
    results = loads(batch.summary_json, [])
    if not isinstance(results, list):
        results = []
    skipped_count = int(getattr(batch, "skipped_count", 0) or 0)
    if not skipped_count:
        skipped_count = sum(1 for item in results if isinstance(item, dict) and item.get("status") == "skipped")
    processed_files = int(batch.success_count or 0) + int(batch.failed_count or 0) + skipped_count
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
        "skipped_count": skipped_count,
        "enable_ai": bool(getattr(batch, "enable_ai", True)),
        "created_at": batch.created_at.isoformat(),
    }
    if include_results:
        data["results"] = results
    return data


def _sync_batch_progress(
    db: Session,
    batch: BatchTask,
    *,
    success: int,
    failed: int,
    skipped: int,
    results: list[dict[str, Any]],
    status: str = "processing",
    force: bool = False,
    index: int = 0,
) -> None:
    batch.success_count = success
    batch.failed_count = failed
    batch.skipped_count = skipped
    batch.summary_json = dumps(results)
    batch.status = status
    if force or (index + 1) % BATCH_PROGRESS_COMMIT_INTERVAL == 0:
        db.commit()


def _finalize_batch_status(success: int, failed: int) -> str:
    if failed and success:
        return "partial_success"
    if failed and not success:
        return "failed"
    return "success"


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

        batch.enable_ai = enable_ai
        try:
            extract_result = safe_extract_zip(zip_path)
            extracted = extract_result.files
            extract_dir = extracted[0].parent if extracted else None
            batch.total_files = len(extracted)
            batch.skipped_count = len(extract_result.skipped)
            batch.summary_json = dumps([])
            db.commit()
        except Exception as exc:
            batch.status = "failed"
            batch.summary_json = dumps(
                [{"filename": zip_path.name, "status": "failed", "error": str(exc), "parse_quality": "low", "parse_warnings": [str(exc)]}]
            )
            batch.failed_count = 1
            batch.success_count = 0
            batch.skipped_count = 0
            batch.total_files = 0
            db.commit()
            return

        results: list[dict[str, Any]] = []
        success = 0
        failed = 0
        skipped = int(batch.skipped_count or 0)
        existing_success = {
            row.original_filename: row
            for row in db.query(AnalysisRecord)
            .filter(AnalysisRecord.batch_task_id == batch_task_id, AnalysisRecord.status == "success")
            .all()
        }

        for skip in extract_result.skipped:
            results.append(
                {
                    "filename": skip["filename"],
                    "status": "skipped",
                    "error": skip["reason"],
                    "parse_quality": "low",
                    "parse_warnings": [skip["reason"]],
                }
            )

        try:
            workers = settings.batch_parallel_workers if enable_ai is False else min(settings.batch_parallel_workers, 2)
            index = 0
            while index < len(extracted):
                db.refresh(batch)
                if batch.status == "paused":
                    _sync_batch_progress(
                        db,
                        batch,
                        success=success,
                        failed=failed,
                        skipped=skipped,
                        results=results,
                        status="paused",
                        force=True,
                    )
                    return

                chunk = extracted[index : index + workers]
                chunk_start = index
                index += len(chunk)

                serial_items: list[tuple[int, Path, dict[str, Any] | None]] = []
                parallel_paths: list[tuple[int, Path]] = []

                for offset, path in enumerate(chunk):
                    absolute_index = chunk_start + offset
                    if path.name.startswith("~$"):
                        skipped += 1
                        results.append(
                            {
                                "filename": path.name,
                                "status": "skipped",
                                "error": "Word 临时文件，已跳过",
                                "parse_quality": "low",
                                "parse_warnings": ["Word 临时文件不是正式简历，系统已跳过。"],
                            }
                        )
                        serial_items.append((absolute_index, path, None))
                        continue
                    prior = existing_success.get(path.name)
                    if prior:
                        prior_sections = loads(prior.sections_json, {})
                        if not isinstance(prior_sections, dict):
                            prior_sections = {}
                        success += 1
                        results.append(
                            {
                                "filename": path.name,
                                "status": "success",
                                "record_id": prior.id,
                                "total_score": float(prior.total_score or 0),
                                "analysis_mode": prior.analysis_mode or "",
                                "analysis_mode_label": public_analysis_mode_label(prior.analysis_mode or "", prior_sections),
                                "parse_quality": "medium",
                                "parse_warnings": [],
                                "reused": True,
                            }
                        )
                        serial_items.append((absolute_index, path, None))
                        continue
                    parallel_paths.append((absolute_index, path))

                if parallel_paths:
                    with ThreadPoolExecutor(max_workers=min(workers, len(parallel_paths))) as pool:
                        future_map = {
                            pool.submit(
                                _analyze_batch_file,
                                path,
                                user_id=user.id,
                                batch_task_id=batch.id,
                                target_position=target_position,
                                job_description=job_description,
                                enable_ai=enable_ai,
                                job_profile_id=job_profile_id or 0,
                                guest_session_id=guest_session_id,
                            ): (absolute_index, path)
                            for absolute_index, path in parallel_paths
                        }
                        for future in as_completed(future_map):
                            absolute_index, path = future_map[future]
                            try:
                                item = future.result()
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
                                        "score_reliability": item.get("score_reliability", "normal"),
                                        "ai_skip_reason": item.get("ai_skip_reason", ""),
                                        "ai_requested": item.get("ai_requested", False),
                                        "ai_enhancement_status": item.get("ai_enhancement_status", "none"),
                                        "ai_enhancement_error": item.get("ai_enhancement_error", ""),
                                    }
                                )
                            except Exception as exc:
                                failed += 1
                                results.append(
                                    {
                                        "filename": path.name,
                                        "status": "failed",
                                        "error": str(exc),
                                        "parse_quality": "low",
                                        "parse_warnings": [str(exc)],
                                    }
                                )
                            _sync_batch_progress(
                                db,
                                batch,
                                success=success,
                                failed=failed,
                                skipped=skipped,
                                results=results,
                                index=absolute_index,
                            )
                elif serial_items:
                    _sync_batch_progress(
                        db,
                        batch,
                        success=success,
                        failed=failed,
                        skipped=skipped,
                        results=results,
                        index=chunk_start + len(chunk) - 1,
                    )

            final_status = _finalize_batch_status(success, failed)
            _sync_batch_progress(
                db,
                batch,
                success=success,
                failed=failed,
                skipped=skipped,
                results=results,
                status=final_status,
                force=True,
            )
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
    enable_ai = bool(getattr(batch, "enable_ai", True))

    batch.status = "processing"
    batch.success_count = 0
    batch.failed_count = 0
    batch.skipped_count = 0
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
        enable_ai=enable_ai,
        job_profile_id=profile.id if profile else None,
        guest_session_id=batch.guest_session_id,
    )
    return batch_to_response(batch, include_results=True, db=db)
