import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.skill import Skill
    from app.models.match import JobMatch


class ResumeSkill(Base):
    """Junction table mapping skills extracted from candidate resumes."""
    __tablename__ = "resume_skills"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    years_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="resume_skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="resume_skills")


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User uploaded and parsed candidate resume."""
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_experience_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    education_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resume")
    resume_skills: Mapped[List["ResumeSkill"]] = relationship(
        "ResumeSkill", back_populates="resume", cascade="all, delete-orphan"
    )
    job_matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="resume", cascade="all, delete-orphan"
    )
