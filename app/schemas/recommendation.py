"""Job recommendation schemas — response models for pgvector-powered job matching."""

from datetime import datetime
from pydantic import BaseModel, Field


class JobRecommendationItem(BaseModel):
    """A single recommended job matched against a resume."""

    job_id: int
    title: str | None = None
    company: str | None = None
    similarity_score: float = Field(..., description="Cosine similarity percentage (0-100)")
    keyword_score: float = Field(..., description="Skill keyword overlap percentage (0-100)")
    overall_score: float = Field(..., description="Blended match score: 60% semantic + 40% keyword")
    matching_skills: list[str] = Field(default_factory=list, description="Skills present in both resume and job")
    missing_skills: list[str] = Field(default_factory=list, description="Job skills missing from resume")
    created_at: datetime

    model_config = {"from_attributes": True}


class JobRecommendationsResponse(BaseModel):
    """Response containing ranked job recommendations for a specific resume."""

    resume_id: int
    resume_file_name: str | None = None
    total_jobs_evaluated: int = Field(..., description="Total candidate jobs evaluated in pgvector catalog")
    returned_count: int = Field(..., description="Number of recommendations returned")
    recommendations: list[JobRecommendationItem] = Field(
        default_factory=list, description="Ranked list of job recommendations (highest score first)"
    )
