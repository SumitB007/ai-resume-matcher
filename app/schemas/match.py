"""Match result schemas — request/response models for match endpoints."""

from datetime import datetime

from pydantic import BaseModel


class MatchResponse(BaseModel):
    """Schema for returning a match result."""

    id: int
    resume_id: int
    job_id: int
    user_id: int
    similarity_score: float | None = None
    keyword_score: float | None = None
    overall_score: float | None = None
    section_scores: dict | None = None
    missing_keywords: list[str] | None = None
    ai_feedback: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    """Schema for listing matches (summary view)."""

    id: int
    resume_id: int
    job_id: int
    overall_score: float | None = None
    similarity_score: float | None = None
    keyword_score: float | None = None
    missing_keywords: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
