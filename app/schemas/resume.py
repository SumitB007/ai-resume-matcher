"""Resume schemas — request/response models for resume endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    """Schema for returning resume data."""

    id: int
    user_id: int
    raw_text: str
    file_name: str | None = None
    parsed_skills: list[str] | None = None
    status: str
    task_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    """Schema for listing resumes (without full text for brevity)."""

    id: int
    user_id: int
    file_name: str | None = None
    status: str
    task_id: str | None = None
    parsed_skills: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

