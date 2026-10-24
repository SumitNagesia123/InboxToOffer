import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job import Job
    from app.models.resume import Resume


class JobMatch(Base, UUIDPrimaryKeyMixin):
    """Explainable job-to-resume matching analysis and score breakdown."""
    __tablename__ = "job_matches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Scores
    overall_match_score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Detailed Explainable Breakdowns
    matched_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_required_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    explanation_summary: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_matches")
    job: Mapped["Job"] = relationship("Job", back_populates="job_matches")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="job_matches")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "resume_id", name="uq_user_job_match"),
        Index("idx_matches_user_score", "user_id", "overall_match_score"),
    )
