"""CoverLetter model — the second document product (Phase 14).

Mirrors ResumeDocument's shape (title, template_id, theme JSON, content JSON)
so the two document products share one mental model, one editor pattern, and
one print pipeline. Content schema (see app/schemas/cover_letter.py):
sender{...}, recipient{name, company, role}, date, greeting, paragraphs[],
closing, signature_name. The resume_id / resume_document_id / job_id links
record what the letter was generated for — provenance, not a live join.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CoverLetter(Base):
    """A cover letter document: structured content + template/theme."""

    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled cover letter")
    template_id: Mapped[str] = mapped_column(String(50), nullable=False, default="classic")
    theme = mapped_column(JSON, nullable=False, default=dict)
    content = mapped_column(JSON, nullable=False, default=dict)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    resume_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("resume_documents.id"), nullable=True
    )
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job_descriptions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<CoverLetter(id={self.id}, title={self.title})>"
