from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.serializers import admin_record_payload, admin_user_payload, audit_log_payload, user_payload
from app.models.entities import AnalysisRecord, AuditLog, BatchTask, JobProfile, Report, User, UserProfile
from app.services.organization import organization_id_for_user
from app.services.teacher_class_stats import teacher_class_distribution
from app.utils.json_tools import loads
from app.utils.time import utc_now


def build_admin_stats(admin: User, db: Session) -> dict[str, Any]:
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    org_id = organization_id_for_user(admin)
    user_base = db.query(User).filter(User.organization_id == org_id)
    record_base = db.query(AnalysisRecord).filter(AnalysisRecord.organization_id == org_id)
    batch_base = db.query(BatchTask).filter(BatchTask.organization_id == org_id)
    return {
        "admin": user_payload(admin),
        "organization_id": org_id,
        "users": {
            "total": user_base.count(),
            "active": user_base.filter(User.status == "active").count(),
            "disabled": user_base.filter(User.status == "disabled").count(),
            "admins": user_base.filter(User.role == "admin").count(),
            "teachers": user_base.filter(User.role == "teacher").count(),
        },
        "records": {
            "total": record_base.count(),
            "today": record_base.filter(AnalysisRecord.created_at >= today_start).count(),
        },
        "batch_tasks": {
            "total": batch_base.count(),
            "processing": batch_base.filter(BatchTask.status.in_(["pending", "processing"])).count(),
        },
        "reports": {
            "total": db.query(Report).filter(Report.organization_id == org_id).count(),
        },
        "audit_logs": {
            "total": db.query(AuditLog).count(),
        },
    }


def build_teacher_stats(user: User, db: Session) -> dict[str, Any]:
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    org_id = organization_id_for_user(user)

    success_filter = (AnalysisRecord.status == "success") & (AnalysisRecord.organization_id == org_id)
    total_records = db.query(func.count(AnalysisRecord.id)).filter(success_filter).scalar() or 0
    today_records = (
        db.query(func.count(AnalysisRecord.id))
        .filter(success_filter, AnalysisRecord.created_at >= today_start)
        .scalar()
        or 0
    )
    week_records = (
        db.query(func.count(AnalysisRecord.id))
        .filter(success_filter, AnalysisRecord.created_at >= week_start)
        .scalar()
        or 0
    )
    avg_score = db.query(func.avg(AnalysisRecord.total_score)).filter(success_filter).scalar() or 0

    score_band = case(
        (AnalysisRecord.total_score < 60, "0-59"),
        (AnalysisRecord.total_score < 70, "60-69"),
        (AnalysisRecord.total_score < 80, "70-79"),
        (AnalysisRecord.total_score < 90, "80-89"),
        else_="90-100",
    )
    bucket_rows = (
        db.query(score_band.label("band"), func.count(AnalysisRecord.id))
        .filter(success_filter)
        .group_by(score_band)
        .all()
    )
    score_buckets = {"0-59": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90-100": 0}
    for band, count in bucket_rows:
        if band in score_buckets:
            score_buckets[band] = int(count)

    daily_rows = (
        db.query(func.date(AnalysisRecord.created_at).label("day"), func.count(AnalysisRecord.id))
        .filter(AnalysisRecord.created_at >= week_start)
        .group_by(func.date(AnalysisRecord.created_at))
        .order_by(func.date(AnalysisRecord.created_at))
        .all()
    )
    daily_volume = [{"date": str(day), "count": int(count)} for day, count in daily_rows]

    school_rows = (
        db.query(UserProfile.school, func.count(UserProfile.id))
        .join(User, User.id == UserProfile.user_id)
        .filter(User.organization_id == org_id, User.role == "user", UserProfile.school != "")
        .group_by(UserProfile.school)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )
    major_rows = (
        db.query(UserProfile.major, func.count(UserProfile.id))
        .join(User, User.id == UserProfile.user_id)
        .filter(User.organization_id == org_id, User.role == "user", UserProfile.major != "")
        .group_by(UserProfile.major)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )
    grade_rows = (
        db.query(UserProfile.grade, func.count(UserProfile.id))
        .join(User, User.id == UserProfile.user_id)
        .filter(User.organization_id == org_id, User.role == "user", UserProfile.grade != "")
        .group_by(UserProfile.grade)
        .order_by(func.count(UserProfile.id).desc())
        .limit(8)
        .all()
    )

    job_rows = (
        db.query(JobProfile.name, func.count(AnalysisRecord.id))
        .join(AnalysisRecord, AnalysisRecord.job_profile_id == JobProfile.id)
        .filter(JobProfile.organization_id == org_id, AnalysisRecord.organization_id == org_id)
        .group_by(JobProfile.name)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(8)
        .all()
    )

    profile_count = (
        db.query(UserProfile)
        .join(User, User.id == UserProfile.user_id)
        .filter(
            User.organization_id == org_id,
            User.role == "user",
            (UserProfile.school != "") | (UserProfile.major != "") | (UserProfile.grade != ""),
        )
        .count()
    )

    major_score_rows = (
        db.query(UserProfile.major, func.avg(AnalysisRecord.total_score), func.count(AnalysisRecord.id))
        .join(User, User.id == UserProfile.user_id)
        .join(AnalysisRecord, AnalysisRecord.user_id == User.id)
        .filter(success_filter, User.organization_id == org_id, User.role == "user", UserProfile.major != "")
        .group_by(UserProfile.major)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(8)
        .all()
    )
    grade_score_rows = (
        db.query(UserProfile.grade, func.avg(AnalysisRecord.total_score), func.count(AnalysisRecord.id))
        .join(User, User.id == UserProfile.user_id)
        .join(AnalysisRecord, AnalysisRecord.user_id == User.id)
        .filter(success_filter, User.organization_id == org_id, User.role == "user", UserProfile.grade != "")
        .group_by(UserProfile.grade)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(8)
        .all()
    )
    class_score_rows = (
        db.query(UserProfile.class_name, func.avg(AnalysisRecord.total_score), func.count(AnalysisRecord.id))
        .join(User, User.id == UserProfile.user_id)
        .join(AnalysisRecord, AnalysisRecord.user_id == User.id)
        .filter(success_filter, User.organization_id == org_id, User.role == "user", UserProfile.class_name != "")
        .group_by(UserProfile.class_name)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(10)
        .all()
    )

    issue_counter: Counter[str] = Counter()
    recent_diagnosis = (
        db.query(AnalysisRecord.diagnosis_json)
        .filter(success_filter)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(200)
        .all()
    )
    for (diag_json,) in recent_diagnosis:
        items = loads(diag_json, [])
        if isinstance(items, list):
            for item in items:
                text = str(item).strip()
                if text:
                    issue_counter[text] += 1

    return {
        "viewer": user_payload(user),
        "summary": {
            "students_with_profile": profile_count,
            "total_records": int(total_records),
            "today_records": int(today_records),
            "week_records": int(week_records),
            "avg_score": round(float(avg_score), 1),
        },
        "score_distribution": [{"band": band, "count": count} for band, count in score_buckets.items()],
        "daily_volume": daily_volume,
        "by_school": [{"name": name or "未填写", "count": int(count)} for name, count in school_rows],
        "by_major": [{"name": name or "未填写", "count": int(count)} for name, count in major_rows],
        "by_grade": [{"name": name or "未填写", "count": int(count)} for name, count in grade_rows],
        "top_job_profiles": [{"name": name, "count": int(count)} for name, count in job_rows],
        "score_by_major": [
            {"name": name or "未填写", "avg_score": round(float(avg or 0), 1), "count": int(count)}
            for name, avg, count in major_score_rows
        ],
        "score_by_grade": [
            {"name": name or "未填写", "avg_score": round(float(avg or 0), 1), "count": int(count)}
            for name, avg, count in grade_score_rows
        ],
        "by_class": teacher_class_distribution(db, org_id),
        "score_by_class": [
            {"name": name or "未填写", "avg_score": round(float(avg or 0), 1), "count": int(count)}
            for name, avg, count in class_score_rows
        ],
        "common_issues": [{"issue": issue, "count": count} for issue, count in issue_counter.most_common(8)],
    }


def list_admin_users(db: Session, organization_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(
            User,
            func.count(func.distinct(AnalysisRecord.id)).label("record_count"),
            func.count(func.distinct(BatchTask.id)).label("batch_count"),
        )
        .filter(User.organization_id == organization_id)
        .outerjoin(AnalysisRecord, AnalysisRecord.user_id == User.id)
        .outerjoin(BatchTask, BatchTask.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [admin_user_payload(user, record_count, batch_count) for user, record_count, batch_count in rows]


def list_admin_records(db: Session, organization_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AnalysisRecord, User)
        .join(User, User.id == AnalysisRecord.user_id)
        .filter(AnalysisRecord.organization_id == organization_id, User.organization_id == organization_id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(500)
        .all()
    )
    profile_ids = {record.job_profile_id for record, _ in rows if record.job_profile_id}
    profile_map = {profile.id: profile.name for profile in db.query(JobProfile).filter(JobProfile.id.in_(profile_ids)).all()} if profile_ids else {}
    for record, _ in rows:
        setattr(record, "_job_profile_name", profile_map.get(record.job_profile_id, ""))
    return [admin_record_payload(record, user) for record, user in rows]


def list_admin_audit_logs(db: Session) -> list[dict[str, Any]]:
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [audit_log_payload(log) for log in logs]
