import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.email import Email
    from app.models.company import Company
    from app.models.skill import Skill
    from app.models.match import JobMatch
    from app.models.application import Application


class JobSkill(Base):
    """Junction table linking required and preferred skills to jobs."""
    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="job_skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_skills")


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted structured job postings."""
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="FULL_TIME", nullable=False)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_source: Mapped[str] = mapped_column(String(100), default="OTHER", index=True, nullable=False)
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Deduplication
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    canonical_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Semantic Vector Embedding (stored as JSON array of floats for maximum portability)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs", foreign_keys=[user_id])
    source_email: Mapped[Optional["Email"]] = relationship("Email", back_populates="jobs")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="jobs")
    job_skills: Mapped[List["JobSkill"]] = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    job_matches: Mapped[List["JobMatch"]] = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_jobs_user_created", "user_id", "created_at"),
        Index("idx_jobs_user_company", "user_id", "company_name"),
        Index("idx_jobs_user_duplicate", "user_id", "is_duplicate"),
    )
