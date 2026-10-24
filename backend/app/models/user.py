import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.oauth import OAuthCredential
    from app.models.email import Email
    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.match import JobMatch
    from app.models.application import Application
    from app.models.preference import UserPreference
    from app.models.audit import DailyDigest, ProcessingRun


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account model for application authentication and multi-tenant data ownership."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    oauth_credential: Mapped[Optional["OAuthCredential"]] = relationship(
        "OAuthCredential", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    emails: Mapped[List["Email"]] = relationship(
        "Email", back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="user", cascade="all, delete-orphan", foreign_keys="[Job.user_id]"
    )
    resume: Mapped[Optional["Resume"]] = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    job_matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    preference: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    daily_digests: Mapped[List["DailyDigest"]] = relationship(
        "DailyDigest", back_populates="user", cascade="all, delete-orphan"
    )
    processing_runs: Mapped[List["ProcessingRun"]] = relationship(
        "ProcessingRun", back_populates="user", cascade="all, delete-orphan"
    )
