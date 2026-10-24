from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import JobSkill
    from app.models.resume import ResumeSkill


class Skill(Base, UUIDPrimaryKeyMixin):
    """Taxonomy master table for technical and soft skills."""
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    job_skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    resume_skills: Mapped[List["ResumeSkill"]] = relationship(
        "ResumeSkill", back_populates="skill", cascade="all, delete-orphan"
    )
