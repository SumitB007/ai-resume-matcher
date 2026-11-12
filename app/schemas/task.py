"""Task schemas — request/response models for background task status tracking."""

from typing import Any
from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    """Schema for Celery background task status."""

    task_id: str
    status: str
    ready: bool
    successful: bool | None = None
    progress: int | None = None
    step: str | None = None
    result: Any = None
    error: str | None = None


class ItemStatusResponse(BaseModel):
    """Schema for checking status of a resume or job processing."""

    id: int
    item_type: str  # "resume" or "job"
    status: str     # "pending", "processing", "completed", "failed"
    task_id: str | None = None
    has_embedding: bool
    skills_count: int
