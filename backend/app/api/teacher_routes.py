from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.platform import build_teacher_stats, require_teacher_or_admin
from app.core.database import get_db

router = APIRouter()


@router.get("/teacher/stats")
def teacher_stats(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = require_teacher_or_admin(request, db)
    return build_teacher_stats(user, db)
