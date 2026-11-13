"""ATS checker schemas (Phase 11 — roadmap Phase 2)."""

from datetime import datetime

from pydantic import BaseModel, Field


class AtsCheckItem(BaseModel):
    """One rule's outcome. `id` is the stable contract across checker versions."""

    id: str
    group: str  # file_parse | contact | sections | content | skills | length_format
    label: str
    status: str  # pass | warn | fail
    detail: str
    weight: int = 1


class AtsCheckResponse(BaseModel):
    """Full ATS readiness result.

    For the authenticated endpoints, id/resume_id/created_at are set (the run
    was persisted). For the anonymous public checker they are null — nothing
    is stored server-side for anonymous checks.
    """

    id: int | None = None
    resume_id: int | None = None
    score: float = Field(..., ge=0, le=100)
    groups: dict[str, float]
    checks: list[AtsCheckItem]
    word_count: int
    skills_found: list[str]
    created_at: datetime | None = None
