"""Generator endpoint schemas (Phase 15, roadmap §9.1)."""

from pydantic import BaseModel, Field


class SummaryGenerateRequest(BaseModel):
    title: str = ""
    years_experience: str = ""
    skills: list[str] = Field(default_factory=list)
    target_role: str = ""
    model: str | None = None


class SummaryVariant(BaseModel):
    label: str
    text: str


class SummaryGenerateResponse(BaseModel):
    variants: list[SummaryVariant]
    model_used: str
    fallback_used: bool


class BulletsGenerateRequest(BaseModel):
    role: str = ""
    company: str = ""
    notes: str = Field(min_length=10)
    model: str | None = None


class BulletsGenerateResponse(BaseModel):
    bullets: list[str]
    model_used: str
    fallback_used: bool


class SuggestSkillsRequest(BaseModel):
    text: str = Field(min_length=20)
    model: str | None = None


class SkillGroupOut(BaseModel):
    name: str
    skills: list[str]


class SuggestSkillsResponse(BaseModel):
    groups: list[SkillGroupOut]
    skills: list[str]
    model_used: str
    fallback_used: bool


class ResumeDraftRequest(BaseModel):
    title: str = Field(min_length=2)
    level: str = Field(default="mid", pattern="^(entry|mid|senior|lead)$")
    skills: str = ""
    model: str | None = None


class ResumeDraftResponse(BaseModel):
    content: dict
    summary_variants: list[SummaryVariant]
    model_used: str
    fallback_used: bool
