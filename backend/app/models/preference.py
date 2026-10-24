import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User preferences for daily job digest and job hunt filters."""
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    digest_time: Mapped[str] = mapped_column(String(10), default="22:00", nullable=False)
    preferred_work_modes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    min_desired_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preference")
