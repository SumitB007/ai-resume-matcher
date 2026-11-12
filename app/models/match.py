"""Match result model — stores the outcome of a resume ↔ job comparison."""

from datetime import datetime

from sqlalchemy import ForeignKey, Float, Text, DateTime, func, ARRAY, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchResult(Base):
    """Result of comparing a resume against a job description."""

    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # ── Scores ──
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Section-Level Scores ──
    section_scores: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # {"skills_match": 0.8, "experience_relevance": 0.6, "keyword_density": 0.7}

    # ── Gap Analysis ──
    missing_keywords = mapped_column(ARRAY(String), nullable=True)

    # ── AI Feedback ──
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ──
    resume = relationship("Resume", back_populates="match_results")
    job = relationship("JobDescription", back_populates="match_results")

    def __repr__(self) -> str:
        return f"<MatchResult(id={self.id}, score={self.overall_score})>"
