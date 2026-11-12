"""Job description model — a job posting with embedding vector."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    DateTime,
    func,
    ARRAY,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobDescription(Base):
    """A job description submitted by a user for matching."""

    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)  # all-MiniLM-L6-v2 → 384 dims
    parsed_skills = mapped_column(ARRAY(String), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | completed | failed
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ──
    owner = relationship("User", back_populates="jobs")
    match_results = relationship(
        "MatchResult", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobDescription(id={self.id}, title={self.title})>"
