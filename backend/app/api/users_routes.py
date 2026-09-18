from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.platform import current_user_from_request, user_payload
from app.api.schemas import UserProfileRequest
from app.core.database import get_db
from app.models.entities import UserProfile

router = APIRouter()


def profile_payload(profile: UserProfile | None) -> dict[str, Any]:
    if not profile:
        return {"school": "", "major": "", "grade": "", "class_name": "", "phone": "", "bio": ""}
    return {
        "school": profile.school or "",
        "major": profile.major or "",
        "grade": profile.grade or "",
        "class_name": profile.class_name or "",
        "phone": profile.phone or "",
        "bio": profile.bio or "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


@router.get("/users/me/profile")
def get_my_profile(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return {"user": user_payload(user), "profile": profile_payload(profile)}


@router.patch("/users/me/profile")
def update_my_profile(payload: UserProfileRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()[:100] or user.display_name
    if payload.school is not None:
        profile.school = payload.school.strip()[:120]
    if payload.major is not None:
        profile.major = payload.major.strip()[:120]
    if payload.grade is not None:
        profile.grade = payload.grade.strip()[:50]
    if payload.class_name is not None:
        profile.class_name = payload.class_name.strip()[:120]
    if payload.phone is not None:
        profile.phone = payload.phone.strip()[:30]
    if payload.bio is not None:
        profile.bio = payload.bio.strip()[:2000]
    db.commit()
    db.refresh(user)
    db.refresh(profile)
    return {"updated": True, "user": user_payload(user), "profile": profile_payload(profile)}
