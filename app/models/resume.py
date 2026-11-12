"""Resume model — uploaded resume with parsed text and embedding vector."""

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


class Resume(Base):
    """An uploaded resume belonging to a user."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)  # all-MiniLM-L6-v2 → 384 dims
    parsed_skills = mapped_column(ARRAY(String), nullable=True)  # extracted skill keywords
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | completed | failed
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ──
    owner = relationship("User", back_populates="resumes")
    match_results = relationship(
        "MatchResult", back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, file={self.file_name}, status={self.status})>"
