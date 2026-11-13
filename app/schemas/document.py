"""Resume document (builder) schemas (Phase 13).

Content is intentionally a free-form dict at the API boundary: the JSON
document schema lives in app/services/document_service.py and evolves in the
editor without Pydantic churn per field. Title/template are validated here;
template must be one of the six known ids.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.document_service import EMPTY_CONTENT, TEMPLATES


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled resume", max_length=255)
    template_id: str = "classic"
    theme: dict = Field(default_factory=dict)
    content: dict = Field(default_factory=lambda: dict(EMPTY_CONTENT))

    @field_validator("template_id")
    @classmethod
    def template_must_exist(cls, value: str) -> str:
        if value not in TEMPLATES:
            raise ValueError(f"Unknown template. Accepted: {', '.join(TEMPLATES)}")
        return value


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    template_id: str | None = None
    theme: dict | None = None
    content: dict | None = None

    @field_validator("template_id")
    @classmethod
    def template_must_exist(cls, value: str | None) -> str | None:
        if value is not None and value not in TEMPLATES:
            raise ValueError(f"Unknown template. Accepted: {', '.join(TEMPLATES)}")
        return value


class DocumentResponse(BaseModel):
    id: int
    title: str
    template_id: str
    theme: dict
    content: dict
    resume_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: int
    title: str
    template_id: str
    resume_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
