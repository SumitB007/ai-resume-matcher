"""Tasks Package — Celery background tasks."""

from app.tasks.celery_app import celery_app
from app.tasks.resume_tasks import process_resume_task
from app.tasks.embedding_tasks import (
    process_job_task,
    generate_text_embedding_task,
    batch_process_embeddings_task,
)
from app.tasks.llm_tasks import generate_match_feedback_task

__all__ = [
    "celery_app",
    "process_resume_task",
    "process_job_task",
    "generate_text_embedding_task",
    "batch_process_embeddings_task",
    "generate_match_feedback_task",
]

