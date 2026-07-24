from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="resume_ai.process_batch_task", bind=True)
def process_batch_task_celery(
    self,
    batch_task_id: int,
    user_id: int,
    zip_path_str: str,
    target_position: str,
    job_description: str,
    enable_ai: bool,
    job_profile_id: int | None = None,
    guest_session_id: str | None = None,
) -> None:
    from app.api.platform import process_batch_task

    process_batch_task(
        batch_task_id,
        user_id,
        zip_path_str,
        target_position,
        job_description,
        enable_ai,
        job_profile_id,
        guest_session_id,
    )


@celery_app.task(name="resume_ai.process_single_analysis", bind=True)
def process_single_analysis_celery(self, record_id: int) -> None:
    from app.api.platform import process_single_analysis

    process_single_analysis(record_id)


@celery_app.task(name="resume_ai.process_ai_enhancement", bind=True)
def process_ai_enhancement_celery(self, record_id: int) -> None:
    from app.api.platform import process_ai_enhancement

    process_ai_enhancement(record_id)
