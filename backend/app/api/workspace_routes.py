from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.actor import resolve_actor
from app.api.platform import delete_history_record, download_report_file, list_report_center, list_task_center
from app.core.database import get_db

router = APIRouter()


@router.get("/tasks")
def tasks(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    return list_task_center(actor, db)


@router.get("/reports")
def reports(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    actor = resolve_actor(request, db)
    return list_report_center(actor, db)


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, request: Request, format: str = "pdf", db: Session = Depends(get_db)):
    return download_report_file(report_id, request, format, db)


@router.delete("/history/{record_id}")
def delete_history(record_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    return delete_history_record(record_id, request, db)
