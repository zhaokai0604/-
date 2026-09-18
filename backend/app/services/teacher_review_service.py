from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AnalysisRecord, User, UserProfile
from app.utils.json_tools import loads


def list_teacher_student_records(db: Session, organization_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AnalysisRecord, User, UserProfile)
        .join(User, User.id == AnalysisRecord.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(User.role == "user", User.organization_id == organization_id, AnalysisRecord.organization_id == organization_id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(500)
        .all()
    )
    items: list[dict[str, Any]] = []
    for record, user, profile in rows:
        diagnosis = loads(record.diagnosis_json, [])
        diagnosis_count = len(diagnosis) if isinstance(diagnosis, list) else 0
        items.append(
            {
                "record_id": record.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "class_name": profile.class_name if profile else "",
                "major": profile.major if profile else "",
                "grade": profile.grade if profile else "",
                "target_position": record.target_position,
                "total_score": record.total_score,
                "status": record.status,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "diagnosis_count": diagnosis_count,
            }
        )
    return items
