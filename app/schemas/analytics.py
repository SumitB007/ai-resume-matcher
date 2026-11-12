"""Analytics schemas — response models for tracking resume progress and match statistics."""

from datetime import datetime
from pydantic import BaseModel, Field


class TimelineMatchEntry(BaseModel):
    """A match record in chronological progression timeline."""

    match_id: int
    resume_id: int
    resume_file_name: str | None = None
    overall_score: float = Field(..., description="Overall match score percentage")
    similarity_score: float | None = None
    keyword_score: float | None = None
    missing_keywords: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeProgressResponse(BaseModel):
    """Tracks score improvements across multiple resume versions for the same job description."""

    job_id: int
    job_title: str | None = None
    job_company: str | None = None
    total_evaluations: int = Field(..., description="Number of resume versions matched against this job")
    initial_score: float | None = Field(None, description="Score of the first resume evaluated")
    latest_score: float | None = Field(None, description="Score of the latest resume evaluated")
    score_improvement: float | None = Field(
        None, description="Net percentage point improvement (latest - initial)"
    )
    average_score: float | None = Field(None, description="Average match score across all versions")
    skills_gained: list[str] = Field(
        default_factory=list,
        description="Skills that were missing in early versions but successfully covered in later versions",
    )
    timeline: list[TimelineMatchEntry] = Field(
        default_factory=list, description="Chronological list of all evaluated matches"
    )


class ResumeJobEvaluationEntry(BaseModel):
    """Summary of a specific job match for a given resume."""

    job_id: int
    job_title: str | None = None
    job_company: str | None = None
    overall_score: float
    similarity_score: float | None = None
    keyword_score: float | None = None
    created_at: datetime


class ResumeEvaluationsSummaryResponse(BaseModel):
    """Summary of all jobs a specific resume has been evaluated against."""

    resume_id: int
    resume_file_name: str | None = None
    total_jobs_matched: int
    average_score: float | None = None
    highest_score: float | None = None
    lowest_score: float | None = None
    matches: list[ResumeJobEvaluationEntry] = Field(default_factory=list)


class SkillFrequency(BaseModel):
    """Frequency count and prevalence of a skill."""

    skill: str
    count: int
    percentage: float = Field(..., description="Percentage of evaluated matches containing this gap")


class UserAnalyticsDashboardResponse(BaseModel):
    """Comprehensive ATS analytics overview for the authenticated user."""

    total_resumes: int
    total_jobs: int
    total_matches: int
    average_match_score: float | None = None
    highest_match_score: float | None = None
    lowest_match_score: float | None = None
    top_missing_skills: list[SkillFrequency] = Field(
        default_factory=list,
        description="Most frequent skill gaps across all matches (skills candidate needs most)",
    )
    top_candidate_skills: list[SkillFrequency] = Field(
        default_factory=list,
        description="Most frequent skills present across candidate resumes",
    )
    recent_matches: list[TimelineMatchEntry] = Field(
        default_factory=list, description="Last 5 matches executed by the user"
    )
