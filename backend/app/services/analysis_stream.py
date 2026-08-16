"""分析过程事件流：真实 pipeline 回调推送；可选边跑边落库。"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any, Iterator

from app.core.database import SessionLocal
from app.models.entities import AnalysisRecord, JobProfile
from app.services.analysis_pipeline import run_analysis_pipeline
from app.utils.json_tools import dumps, loads

_live_running: set[int] = set()
_live_lock = threading.Lock()


def _event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps({"event": event, **data}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def iter_analysis_events(
    path: Path,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    profile: JobProfile | None = None,
    *,
    pace_seconds: float = 0.0,
) -> Iterator[str]:
    """边跑 pipeline 边推送真实事件；done 携带完整 pipeline 结果。"""
    del pace_seconds  # 保留参数兼容，真实流不再人为拖延主链路
    event_q: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
    holder: dict[str, Any] = {}

    def sink(event: str, data: dict[str, Any]) -> None:
        event_q.put((event, data))

    def worker() -> None:
        try:
            holder["pipeline"] = run_analysis_pipeline(
                path,
                target_position,
                job_description,
                enable_ai,
                profile,
                event_sink=sink,
            )
        except Exception as exc:  # noqa: BLE001 - 推给前端展示
            holder["error"] = str(exc)
        finally:
            event_q.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        item = event_q.get()
        if item is None:
            break
        event, data = item
        yield _event(event, data)

    if holder.get("error"):
        yield _event("stream_error", {"message": holder["error"]})
        return

    pipeline = holder.get("pipeline") or {}
    result = pipeline.get("result") if isinstance(pipeline.get("result"), dict) else {}
    rewrite = result.get("rewrite_preview") if isinstance(result.get("rewrite_preview"), dict) else {}
    optimized = rewrite.get("optimized_resume") if isinstance(rewrite.get("optimized_resume"), dict) else {}
    yield _event(
        "done",
        {
            "message": "分析完成，已生成基于初稿的优化稿",
            "total_score": result.get("total_score"),
            "change_count": optimized.get("change_count", 0),
            "pipeline": {
                "result": result,
                "sections_payload": pipeline.get("sections_payload"),
                "mode": pipeline.get("mode"),
                "target_position": pipeline.get("target_position"),
                "job_description": pipeline.get("job_description"),
                "parsed": pipeline.get("parsed"),
            },
        },
    )


def iter_live_analysis_and_persist(record_id: int) -> Iterator[str]:
    """对 processing 记录跑真实 pipeline，边推 SSE，done 时落库。"""
    from app.api.platform import apply_pipeline_result_to_record, get_source_resume_file

    with _live_lock:
        if record_id in _live_running:
            yield _event("stream_error", {"message": "该分析已在流式处理中，请勿重复连接。"})
            return
        _live_running.add(record_id)

    try:
        with SessionLocal() as db:
            record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
            if not record:
                yield _event("stream_error", {"message": "记录不存在。"})
                return
            if record.status == "success":
                yield _event(
                    "done",
                    {
                        "message": "分析已完成",
                        "total_score": record.total_score,
                        "record_id": record.id,
                        "already_done": True,
                    },
                )
                return
            if record.status != "processing":
                yield _event("stream_error", {"message": f"当前状态不可流式分析：{record.status}"})
                return

            upload = get_source_resume_file(db, record.id, record.user_id)
            if not upload or not Path(upload.stored_path).exists():
                record.status = "failed"
                record.error_message = "找不到原始简历文件。"
                db.commit()
                yield _event("stream_error", {"message": record.error_message})
                return

            path = Path(upload.stored_path)
            job_meta = loads(record.sections_json, {}).get("_job", {})
            if not isinstance(job_meta, dict):
                job_meta = {}
            enable_ai = bool(job_meta.get("enable_ai", True))
            target_match_enabled = bool(job_meta.get("target_match_enabled", False))
            profile = (
                db.query(JobProfile).filter(JobProfile.id == record.job_profile_id).first()
                if target_match_enabled and record.job_profile_id
                else None
            )
            target_position = record.target_position if target_match_enabled else ""
            job_description = record.job_description if target_match_enabled else ""
            # 标记已认领，防止后台误跑
            job_meta["stream"] = True
            job_meta["live_claimed"] = True
            sections = loads(record.sections_json, {})
            if not isinstance(sections, dict):
                sections = {}
            sections["_job"] = job_meta
            record.sections_json = dumps(sections)
            db.commit()

        event_q: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
        holder: dict[str, Any] = {}

        def sink(event: str, data: dict[str, Any]) -> None:
            event_q.put((event, data))

        def worker() -> None:
            try:
                holder["pipeline"] = run_analysis_pipeline(
                    path,
                    target_position,
                    job_description,
                    enable_ai,
                    profile,
                    event_sink=sink,
                )
            except Exception as exc:  # noqa: BLE001
                holder["error"] = str(exc)
            finally:
                event_q.put(None)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        while True:
            item = event_q.get()
            if item is None:
                break
            event, data = item
            yield _event(event, data)

        if holder.get("error"):
            with SessionLocal() as db:
                record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
                if record and record.status == "processing":
                    record.status = "failed"
                    record.error_message = str(holder["error"])
                    db.commit()
            yield _event("stream_error", {"message": holder["error"], "record_id": record_id})
            return

        pipeline = holder.get("pipeline") or {}
        with SessionLocal() as db:
            record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
            if not record:
                yield _event("stream_error", {"message": "记录在落库前丢失。"})
                return
            if record.status == "processing":
                apply_pipeline_result_to_record(db, record, pipeline)
            result = pipeline.get("result") if isinstance(pipeline.get("result"), dict) else {}
            rewrite = result.get("rewrite_preview") if isinstance(result.get("rewrite_preview"), dict) else {}
            optimized = rewrite.get("optimized_resume") if isinstance(rewrite.get("optimized_resume"), dict) else {}
            yield _event(
                "done",
                {
                    "message": "分析完成，结果已落库",
                    "total_score": result.get("total_score", record.total_score),
                    "change_count": optimized.get("change_count", 0),
                    "record_id": record_id,
                    "persisted": True,
                },
            )
    finally:
        with _live_lock:
            _live_running.discard(record_id)
