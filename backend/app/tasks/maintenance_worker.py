from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="resume_ai.maintain_records")
def maintain_records_celery() -> dict[str, int]:
    from app.core.database import SessionLocal
    from app.services.record_maintenance import recover_stale_records_batch, repair_legacy_records_batch

    with SessionLocal() as db:
        return {
            "legacy_repaired": repair_legacy_records_batch(db, limit=50),
            "stale_recovered": recover_stale_records_batch(db, limit=50),
        }
