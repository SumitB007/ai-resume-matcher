"""LLM schemas — request/response models for AI-powered feedback, bullet rewrites, and skill extraction."""

from pydantic import BaseModel, Field


class BulletRewriteRequest(BaseModel):
    """Request to rewrite a resume bullet point."""

    bullet: str = Field(
        ...,
        min_length=10,
        description="The bullet point to rewrite and improve",
        examples=["Worked on backend APIs and databases for our web app."],
    )
    target_job: str | None = Field(
        None,
        description="Optional target job description or requirements context",
        examples=["Senior Python Developer with FastAPI, PostgreSQL, and Redis expertise."],
    )
    missing_skills: list[str] | None = Field(
        None,
        description="Skills or keywords to weave into the rewritten statement",
        examples=["FastAPI", "Redis", "PostgreSQL"],
    )
    model: str | None = Field(
        None,
        description="Optional OpenRouter model override (e.g. 'mistralai/mistral-7b-instruct:free')",
    )


class BulletRewriteResponse(BaseModel):
    """Response containing rewritten bullet points and improvements."""

    original_bullet: str
    rewrite_content: str
    model_used: str
    fallback_used: bool = False


class LLMSkillExtractionRequest(BaseModel):
    """Request for LLM-based technical skill extraction."""

    text: str = Field(
        ...,
        min_length=20,
        description="Resume text or job description to extract technical competencies from",
    )
    model: str | None = Field(
        None,
        description="Optional OpenRouter model override",
    )


class LLMSkillExtractionResponse(BaseModel):
    """Response containing extracted skills."""

    skills: list[str]
    count: int
    model_used: str
    fallback_used: bool = False


class MatchFeedbackRequest(BaseModel):
    """Optional configuration when requesting match feedback."""

    model: str | None = Field(
        None,
        description="Optional OpenRouter model override",
    )


class MatchFeedbackResponse(BaseModel):
    """Feedback response for a match result."""

    match_id: int
    ai_feedback: str
    model_used: str
    fallback_used: bool = False


class ModelListResponse(BaseModel):
    """Response listing recommended models available for selection."""

    default_model: str
    recommended_models: list[dict]
