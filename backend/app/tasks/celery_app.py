from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery("resume_ai", broker=settings.redis_url or "redis://localhost:6379/0", backend=settings.redis_url or "redis://localhost:6379/0")
celery_app.conf.update(
    imports=("app.tasks.batch_worker", "app.tasks.maintenance_worker"),
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "maintain-records-every-minute": {
            "task": "resume_ai.maintain_records",
            "schedule": 60.0,
        },
    },
)


def celery_enabled() -> bool:
    return bool(settings.redis_url) and settings.use_celery
