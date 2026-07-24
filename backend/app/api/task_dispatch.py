from __future__ import annotations

from typing import Any

from app.tasks.batch_worker import process_batch_task_celery, process_single_analysis_celery
from app.tasks.celery_app import celery_enabled


def dispatch_batch_task(background_tasks: Any, **kwargs) -> None:
    if celery_enabled():
        process_batch_task_celery.delay(**kwargs)
        return
    from app.api.platform import process_batch_task

    background_tasks.add_task(process_batch_task, **kwargs)


def dispatch_single_analysis(background_tasks: Any, record_id: int) -> None:
    if celery_enabled():
        process_single_analysis_celery.delay(record_id)
        return
    from app.api.platform import process_single_analysis

    background_tasks.add_task(process_single_analysis, record_id)
