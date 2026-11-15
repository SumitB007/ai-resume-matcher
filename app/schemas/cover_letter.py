"""Cover letter schemas (Phase 14).

Content is a free-form dict at the API boundary, like documents: the letter
shape (sender / recipient / greeting / paragraphs / closing / signature)
evolves in the editor without Pydantic churn per field. Templates are the
same six ids as resumes — a letter visually matches its resume.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.document_service import TEMPLATES

EMPTY_LETTER_CONTENT: dict = {
    "sender": {"name": "", "title": "", "email": "", "phone": "", "location": ""},
    "recipient": {"name": "", "company": "", "role": ""},
    "date": "",
    "greeting": "Dear Hiring Manager,",
    "paragraphs": [],
    "closing": "Sincerely,",
    "signature_name": "",
}


def _validate_template(value: str | None) -> str | None:
    if value is not None and value not in TEMPLATES:
        raise ValueError(f"Unknown template. Accepted: {', '.join(TEMPLATES)}")
    return value


class CoverLetterCreate(BaseModel):
    title: str = Field(default="Untitled cover letter", max_length=255)
    template_id: str = "classic"
    theme: dict = Field(default_factory=dict)
    content: dict = Field(default_factory=lambda: dict(EMPTY_LETTER_CONTENT))
    resume_id: int | None = None
    resume_document_id: int | None = None
    job_id: int | None = None

    _check_template = field_validator("template_id")(_validate_template)


class CoverLetterUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    template_id: str | None = None
    theme: dict | None = None
    content: dict | None = None

    _check_template = field_validator("template_id")(_validate_template)


class CoverLetterResponse(BaseModel):
    id: int
    title: str
    template_id: str
    theme: dict
    content: dict
    resume_id: int | None = None
    resume_document_id: int | None = None
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoverLetterListItem(BaseModel):
    id: int
    title: str
    template_id: str
    resume_id: int | None = None
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoverLetterGenerateRequest(BaseModel):
    """One-click generation: a resume (uploaded, or a built document's synced
    resume) plus a job (saved, or pasted text) → a saved editable letter."""

    resume_id: int | None = None
    resume_document_id: int | None = None
    job_id: int | None = None
    job_text: str | None = None
    job_title: str | None = None
    company: str | None = None
    recipient_name: str | None = None
    tone: str = Field(default="professional", pattern="^(professional|enthusiastic|concise)$")
    model: str | None = None
    template_id: str = "classic"

    _check_template = field_validator("template_id")(_validate_template)


class AiCoverLetterRequest(BaseModel):
    """Stateless generation (roadmap §8: POST /ai/cover-letter)."""

    resume_text: str = Field(min_length=50)
    job_text: str = Field(min_length=30)
    job_title: str = ""
    company: str = ""
    tone: str = Field(default="professional", pattern="^(professional|enthusiastic|concise)$")
    model: str | None = None


class AiCoverLetterResponse(BaseModel):
    paragraphs: list[str]
    model_used: str
    fallback_used: bool
