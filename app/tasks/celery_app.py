"""Celery application configuration.

Phase 7: Celery Background Tasks with Redis as broker and result backend.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "ats_matcher",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.resume_tasks",
        "app.tasks.embedding_tasks",
        "app.tasks.llm_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # Results kept for 24 hours
)

# Ensure task registration upon celery_app import
from app.tasks import resume_tasks, embedding_tasks, llm_tasks  # noqa: E402, F401


