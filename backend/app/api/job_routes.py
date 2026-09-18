from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.actor import actor_guest_session_value, job_profile_owned_by_actor, resolve_actor, scope_job_profiles
from app.api.platform import job_profile_payload, normalize_job_profile_payload
from app.api.schemas import JobProfileRequest
from app.core.database import get_db
from app.models.entities import JobProfile
from app.services.job_market import list_public_jobs
from app.services.job_profile_presets import get_job_profile_preset, list_job_profile_presets, preset_payload

router = APIRouter()


@router.get("/job-market")
def job_market(city: str = "", category: str = "", education: str = "") -> dict[str, Any]:
    """Expose verified detail-page jobs; search-result candidates stay hidden."""
    items = list_public_jobs()
    filters = [city.strip().lower(), category.strip().lower(), education.strip().lower()]
    filtered = []
    for item in items:
        values = [str(item.get("city", "")).lower(), str(item.get("category", "")).lower(), str(item.get("education", "")).lower()]
        if all(not needle or needle in value for needle, value in zip(filters, values)):
            filtered.append(item)
    return {"items": filtered, "total": len(filtered), "verified_total": len(items)}


@router.get("/job-profiles")
def job_profiles(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    actor = resolve_actor(request, db)
    profiles = (
        scope_job_profiles(db.query(JobProfile), actor)
        .filter(JobProfile.status != "archived")
        .order_by(JobProfile.updated_at.desc(), JobProfile.created_at.desc())
        .all()
    )
    return [job_profile_payload(item) for item in profiles]


@router.get("/job-profile-presets")
def job_profile_presets() -> list[dict[str, Any]]:
    return list_job_profile_presets()


@router.post("/job-profile-presets/{preset_id}/copy")
def copy_job_profile_preset(preset_id: str, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    preset = get_job_profile_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="系统岗位模板不存在。")
    payload = preset_payload(preset)
    existing = (
        scope_job_profiles(db.query(JobProfile), actor)
        .filter(
            JobProfile.status != "archived",
            JobProfile.name == payload["name"],
            JobProfile.category == payload["category"],
            JobProfile.target_position == payload["target_position"],
        )
        .first()
    )
    if existing:
        return {"created": False, "profile": job_profile_payload(existing)}

    profile = JobProfile(
        user_id=actor.user.id,
        organization_id=actor.organization_id,
        guest_session_id=actor_guest_session_value(actor),
        **payload,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"created": True, "profile": job_profile_payload(profile)}


@router.post("/job-profiles")
def create_job_profile(payload: JobProfileRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    normalized = normalize_job_profile_payload(payload)
    profile = JobProfile(
        user_id=actor.user.id,
        organization_id=actor.organization_id,
        guest_session_id=actor_guest_session_value(actor),
        **normalized,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return job_profile_payload(profile)


@router.put("/job-profiles/{job_profile_id}")
def update_job_profile(job_profile_id: int, payload: JobProfileRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    profile = db.query(JobProfile).filter(JobProfile.id == job_profile_id).first()
    if not profile or not job_profile_owned_by_actor(profile, actor):
        raise HTTPException(status_code=404, detail="岗位模板不存在。")
    normalized = normalize_job_profile_payload(payload)
    for key, value in normalized.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return job_profile_payload(profile)


@router.delete("/job-profiles/{job_profile_id}")
def delete_job_profile(job_profile_id: int, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    actor = resolve_actor(request, db)
    profile = db.query(JobProfile).filter(JobProfile.id == job_profile_id).first()
    if not profile or not job_profile_owned_by_actor(profile, actor):
        raise HTTPException(status_code=404, detail="岗位模板不存在。")
    profile.status = "archived"
    db.commit()
    return {"deleted": True, "job_profile_id": job_profile_id}
