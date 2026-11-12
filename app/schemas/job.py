"""Job description schemas — request/response models for job endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Schema for submitting a job description."""

    raw_text: str = Field(
        ...,
        min_length=50,
        description="Full job description text",
        examples=["We are looking for a Senior Python Developer with 5+ years of experience..."],
    )
    title: str | None = Field(
        None, max_length=255, examples=["Senior Python Developer"]
    )
    company: str | None = Field(None, max_length=255, examples=["Acme Corp"])


class JobResponse(BaseModel):
    """Schema for returning job description data."""

    id: int
    user_id: int
    raw_text: str
    title: str | None = None
    company: str | None = None
    parsed_skills: list[str] | None = None
    status: str
    task_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Schema for listing jobs (without full text)."""

    id: int
    user_id: int
    title: str | None = None
    company: str | None = None
    status: str
    task_id: str | None = None
    parsed_skills: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

