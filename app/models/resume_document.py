"""ResumeDocument model — a structured, builder-created resume (Phase 13).

WHY A SEPARATE MODEL (decisions.md §13.1): an uploaded Resume is extracted
text + embedding; a built resume is a structured document (sections, entries,
bullets) plus presentation choices (template, theme). Squashing the document
into Resume would lose the structure the editor needs. Instead the document
keeps its JSON content as the source of truth, and on demand it *syncs* into
the existing pipeline: its flattened text becomes a normal Resume row (linked
via resume_id) that matching/ATS treat exactly like an upload.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResumeDocument(Base):
    """A resume built in the browser: structured content + template/theme."""

    __tablename__ = "resume_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled resume")
    template_id: Mapped[str] = mapped_column(String(50), nullable=False, default="classic")
    # theme: {"accent": "#1d4ed8", "font": "sans", "density": "normal"}
    theme = mapped_column(JSON, nullable=False, default=dict)
    # content: the structured document (schema in app/services/document_service.py)
    content = mapped_column(JSON, nullable=False, default=dict)
    # The pipeline twin: the Resume row created from this document's flattened
    # text by POST /documents/{id}/sync-resume. Null until first sync.
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ResumeDocument(id={self.id}, title={self.title}, template={self.template_id})>"
