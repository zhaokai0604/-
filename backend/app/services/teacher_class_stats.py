"""教师端班级维度统计。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import AnalysisRecord, User, UserProfile
from app.utils.json_tools import loads


def class_label(profile: UserProfile) -> str:
    name = (profile.class_name or "").strip()
    if name:
        return name
    parts = [part.strip() for part in (profile.major or "", profile.grade or "") if part and part.strip()]
    return " · ".join(parts) if parts else "未分班"


def build_teacher_class_panel(db: Session) -> dict[str, Any]:
    success_filter = AnalysisRecord.status == "success"
    profiles = db.query(UserProfile).all()
    label_map: dict[str, dict[str, Any]] = {}

    for profile in profiles:
        label = class_label(profile)
        bucket = label_map.setdefault(
            label,
            {
                "name": label,
                "student_count": 0,
                "record_count": 0,
                "score_sum": 0.0,
                "majors": set(),
                "grades": set(),
                "top_positions": {},
            },
        )
        bucket["student_count"] += 1
        if profile.major:
            bucket["majors"].add(profile.major.strip())
        if profile.grade:
            bucket["grades"].add(profile.grade.strip())

    record_rows = (
        db.query(AnalysisRecord, UserProfile)
        .join(User, User.id == AnalysisRecord.user_id)
        .join(UserProfile, UserProfile.user_id == User.id)
        .filter(success_filter)
        .all()
    )
    for record, profile in record_rows:
        label = class_label(profile)
        bucket = label_map.setdefault(
            label,
            {
                "name": label,
                "student_count": 0,
                "record_count": 0,
                "score_sum": 0.0,
                "majors": set(),
                "grades": set(),
                "top_positions": {},
            },
        )
        bucket["record_count"] += 1
        bucket["score_sum"] += float(record.total_score or 0)
        position = (record.target_position or "未指定").strip() or "未指定"
        bucket["top_positions"][position] = bucket["top_positions"].get(position, 0) + 1

    classes: list[dict[str, Any]] = []
    for label, bucket in label_map.items():
        if bucket["record_count"] == 0 and bucket["student_count"] == 0:
            continue
        avg_score = round(bucket["score_sum"] / bucket["record_count"], 1) if bucket["record_count"] else 0.0
        top_positions = sorted(bucket["top_positions"].items(), key=lambda item: item[1], reverse=True)[:3]
        classes.append(
            {
                "name": label,
                "student_count": bucket["student_count"],
                "record_count": bucket["record_count"],
                "avg_score": avg_score,
                "majors": sorted(bucket["majors"])[:5],
                "grades": sorted(bucket["grades"])[:5],
                "top_positions": [{"name": name, "count": count} for name, count in top_positions],
            }
        )

    classes.sort(key=lambda item: (item["record_count"], item["student_count"]), reverse=True)

    issue_counter: dict[str, int] = {}
    for record, profile in record_rows[:300]:
        label = class_label(profile)
        if not any(item["name"] == label for item in classes[:8]):
            continue
        diagnosis = loads(record.diagnosis_json, [])
        if isinstance(diagnosis, list):
            for item in diagnosis:
                text = str(item).strip()
                if text:
                    issue_counter[text] = issue_counter.get(text, 0) + 1

    return {
        "summary": {
            "class_count": len(classes),
            "students_with_profile": sum(item["student_count"] for item in classes),
            "total_records": sum(item["record_count"] for item in classes),
        },
        "classes": classes[:20],
        "common_issues": [{"issue": issue, "count": count} for issue, count in sorted(issue_counter.items(), key=lambda x: -x[1])[:8]],
    }


def teacher_class_distribution(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(UserProfile.class_name, func.count(UserProfile.id))
        .filter(UserProfile.class_name != "")
        .group_by(UserProfile.class_name)
        .order_by(func.count(UserProfile.id).desc())
        .limit(10)
        .all()
    )
    return [{"name": name or "未填写", "count": int(count)} for name, count in rows]
