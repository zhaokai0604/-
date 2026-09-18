"""组织（学校/租户）上下文与默认租户初始化。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Organization, User

DEFAULT_ORG_CODE = "default"


def ensure_default_organization(db: Session) -> Organization:
    org = db.query(Organization).filter(Organization.code == DEFAULT_ORG_CODE).first()
    if org:
        return org
    org = Organization(
        name=settings.default_organization_name,
        code=DEFAULT_ORG_CODE,
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def organization_id_for_user(user: User | None) -> int:
    if user is None:
        return settings.default_organization_id
    org_id = getattr(user, "organization_id", None)
    return int(org_id or settings.default_organization_id)


def scope_users_by_organization(query, organization_id: int):
    return query.filter(User.organization_id == organization_id)


def scope_records_by_organization(query, organization_id: int, record_model):
    return query.filter(record_model.organization_id == organization_id)
