"""ATS check result model — a persisted standalone ATS readiness check.

Phase 11 (roadmap Phase 2): stores the outcome of ats_service.run_ats_checks
for a user's resume so the result survives reloads and history can be shown.
Anonymous public checks are never persisted (no row is created for them).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AtsCheckResult(Base):
    """One ATS readiness check run against one resume."""

    __tablename__ = "ats_check_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    # Full checker payload: {"groups": {...}, "checks": [...], "word_count": int,
    # "skills_found": [...]} — stored whole so check definitions can evolve
    # without schema changes (the check ids inside are the stable contract).
    result = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AtsCheckResult(id={self.id}, resume={self.resume_id}, score={self.score})>"
