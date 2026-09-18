from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.platform import build_teacher_stats, require_teacher_or_admin
from app.api.schemas import TeacherTrainingTaskRequest
from app.core.database import get_db
from app.services.organization import organization_id_for_user
from app.services.teacher_class_stats import build_teacher_class_panel
from app.services.teacher_review_service import list_teacher_student_records
from app.services.teacher_training import create_class_training_task

router = APIRouter()


@router.get("/teacher/stats")
def teacher_stats(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = require_teacher_or_admin(request, db)
    return build_teacher_stats(user, db)


@router.get("/teacher/classes")
def teacher_classes(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = require_teacher_or_admin(request, db)
    return build_teacher_class_panel(db, organization_id_for_user(user))


@router.get("/teacher/records")
def teacher_records(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = require_teacher_or_admin(request, db)
    return {"items": list_teacher_student_records(db, organization_id_for_user(user))}


@router.post("/teacher/training-tasks")
def teacher_training_task(
    payload: TeacherTrainingTaskRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """基于共性问题生成班级训练任务（一键成课）。"""
    require_teacher_or_admin(request, db)
    try:
        task = create_class_training_task(db, issue=payload.issue, class_name=payload.class_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"task": task}


@router.get("/teacher/stats/export")
def teacher_stats_export(request: Request, db: Session = Depends(get_db)) -> Response:
    user = require_teacher_or_admin(request, db)
    stats = build_teacher_stats(user, db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["指标", "数值"])
    summary = stats.get("summary") or {}
    for key, value in summary.items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(["分数段", "人数"])
    for item in stats.get("score_distribution") or []:
        writer.writerow([item.get("band"), item.get("count")])
    writer.writerow([])
    writer.writerow(["日期", "分析量"])
    for item in stats.get("daily_volume") or []:
        writer.writerow([item.get("date"), item.get("count")])
    writer.writerow([])
    writer.writerow(["专业", "均分", "分析量"])
    for item in stats.get("score_by_major") or []:
        writer.writerow([item.get("name"), item.get("avg_score"), item.get("count")])
    writer.writerow([])
    writer.writerow(["年级", "均分", "分析量"])
    for item in stats.get("score_by_grade") or []:
        writer.writerow([item.get("name"), item.get("avg_score"), item.get("count")])
    writer.writerow([])
    writer.writerow(["班级", "人数"])
    for item in stats.get("by_class") or []:
        writer.writerow([item.get("name"), item.get("count")])
    writer.writerow([])
    writer.writerow(["班级", "均分", "分析量"])
    for item in stats.get("score_by_class") or []:
        writer.writerow([item.get("name"), item.get("avg_score"), item.get("count")])
    writer.writerow([])
    writer.writerow(["共性问题", "出现次数"])
    for item in stats.get("common_issues") or []:
        writer.writerow([item.get("issue"), item.get("count")])
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="teacher-stats.csv"'},
    )
