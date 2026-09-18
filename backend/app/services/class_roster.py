"""班级花名册导入：管理员批量创建/更新学生账号与班级信息。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.platform import generate_temp_password
from app.models.entities import User, UserProfile
from app.services.auth import hash_password, validate_username
from app.services.organization import organization_id_for_user
from app.utils.time import utc_now


def import_class_roster(
    db: Session,
    admin: User,
    rows: list[dict[str, Any]],
    *,
    create_missing: bool = True,
) -> dict[str, int]:
    organization_id = organization_id_for_user(admin)
    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for index, raw in enumerate(rows, start=1):
        username_raw = str(raw.get("username") or raw.get("学号") or "").strip()
        if not username_raw:
            skipped += 1
            continue
        try:
            username = validate_username(username_raw)
        except HTTPException as exc:
            errors.append(f"第 {index} 行: {exc.detail}")
            skipped += 1
            continue

        display_name = str(raw.get("display_name") or raw.get("姓名") or username).strip()[:100]
        class_name = str(raw.get("class_name") or raw.get("班级") or "").strip()[:120]
        major = str(raw.get("major") or raw.get("专业") or "").strip()[:120]
        grade = str(raw.get("grade") or raw.get("年级") or "").strip()[:50]
        school = str(raw.get("school") or raw.get("学校") or "").strip()[:120]

        user = db.query(User).filter(User.username == username).first()
        if user and user.organization_id not in {organization_id, None} and getattr(user, "organization_id", organization_id) != organization_id:
            errors.append(f"第 {index} 行: 用户 {username} 属于其他组织")
            skipped += 1
            continue

        if not user:
            if not create_missing:
                skipped += 1
                continue
            temp_password = generate_temp_password()
            user = User(
                username=username,
                display_name=display_name or username,
                password_hash=hash_password(temp_password),
                role="user",
                status="active",
                organization_id=organization_id,
            )
            db.add(user)
            db.flush()
            created += 1
        else:
            if user.role not in {"user", "teacher"}:
                errors.append(f"第 {index} 行: 用户 {username} 不是学生/教师账号，已跳过")
                skipped += 1
                continue
            if display_name and user.display_name != display_name:
                user.display_name = display_name
            if getattr(user, "organization_id", None) != organization_id:
                user.organization_id = organization_id
            updated += 1

        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if not profile:
            profile = UserProfile(user_id=user.id)
            db.add(profile)
            db.flush()
        if class_name:
            profile.class_name = class_name
        if major:
            profile.major = major
        if grade:
            profile.grade = grade
        if school:
            profile.school = school
        profile.updated_at = utc_now()

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "total": len(rows),
    }
