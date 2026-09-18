from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.core.database import ensure_guest_user
from app.models.entities import AnalysisRecord, BatchTask, JobProfile, Report, User
from app.services.auth import parse_session_token
from app.services.organization import organization_id_for_user


@dataclass
class ActorContext:
    user: User
    guest_session_id: str | None = None
    organization_id: int = 1

    @property
    def is_guest(self) -> bool:
        return self.user.username == settings.default_user_name


def current_user_from_request(request: Request, db: Session) -> User | None:
    payload = parse_session_token(request.cookies.get(settings.session_cookie_name))
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.username == settings.default_user_name or user.status != "active":
        return None
    return user


def resolve_actor(request: Request, db: Session) -> ActorContext:
    user = current_user_from_request(request, db)
    if user:
        return ActorContext(user=user, organization_id=organization_id_for_user(user))
    guest = ensure_guest_user(db, User)
    session_id = getattr(request.state, "guest_session_id", None)
    return ActorContext(
        user=guest,
        guest_session_id=session_id,
        organization_id=organization_id_for_user(guest),
    )


def guest_session_id_from_request(request: Request) -> str | None:
    return getattr(request.state, "guest_session_id", None) or request.cookies.get(settings.guest_session_cookie_name)


def scope_records(query: Query, actor: ActorContext) -> Query:
    query = query.filter(AnalysisRecord.organization_id == actor.organization_id)
    query = query.filter(AnalysisRecord.user_id == actor.user.id)
    if actor.is_guest:
        if actor.guest_session_id:
            query = query.filter(AnalysisRecord.guest_session_id == actor.guest_session_id)
        else:
            query = query.filter(AnalysisRecord.id < 0)
    return query


def scope_batches(query: Query, actor: ActorContext) -> Query:
    query = query.filter(BatchTask.organization_id == actor.organization_id)
    query = query.filter(BatchTask.user_id == actor.user.id)
    if actor.is_guest:
        if actor.guest_session_id:
            query = query.filter(BatchTask.guest_session_id == actor.guest_session_id)
        else:
            query = query.filter(BatchTask.id < 0)
    return query


def scope_reports(query: Query, actor: ActorContext) -> Query:
    query = query.filter(Report.organization_id == actor.organization_id)
    query = query.filter(Report.user_id == actor.user.id)
    if actor.is_guest:
        if actor.guest_session_id:
            query = query.filter(Report.guest_session_id == actor.guest_session_id)
        else:
            query = query.filter(Report.id < 0)
    return query


def actor_guest_session_value(actor: ActorContext) -> str | None:
    return actor.guest_session_id if actor.is_guest else None


def scope_job_profiles(query: Query, actor: ActorContext) -> Query:
    query = query.filter(JobProfile.organization_id == actor.organization_id)
    query = query.filter(JobProfile.user_id == actor.user.id)
    if actor.is_guest:
        if actor.guest_session_id:
            query = query.filter(JobProfile.guest_session_id == actor.guest_session_id)
        else:
            query = query.filter(JobProfile.id < 0)
    else:
        query = query.filter(JobProfile.guest_session_id.is_(None))
    return query


def job_profile_owned_by_actor(profile: JobProfile, actor: ActorContext) -> bool:
    if profile.organization_id != actor.organization_id or profile.user_id != actor.user.id:
        return False
    if actor.is_guest:
        return bool(actor.guest_session_id) and profile.guest_session_id == actor.guest_session_id
    return profile.guest_session_id is None


def record_owned_by_actor(record: AnalysisRecord, actor: ActorContext) -> bool:
    if record.organization_id != actor.organization_id or record.user_id != actor.user.id:
        return False
    if actor.is_guest:
        return bool(actor.guest_session_id) and record.guest_session_id == actor.guest_session_id
    return True


def batch_owned_by_actor(batch: BatchTask, actor: ActorContext) -> bool:
    if batch.organization_id != actor.organization_id or batch.user_id != actor.user.id:
        return False
    if actor.is_guest:
        return bool(actor.guest_session_id) and batch.guest_session_id == actor.guest_session_id
    return True
