import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class EmailRejectLog(Base, UUIDPrimaryKeyMixin):
    """
    Log of emails evaluated and discarded by the job triage guardrail.
    Does NOT store email body to respect candidate privacy.
    Used to skip re-evaluating or re-fetching discarded messages in future syncs.
    """
    __tablename__ = "email_reject_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    gmail_message_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("idx_reject_logs_user_msg", "user_id", "gmail_message_id"),
        Index("idx_reject_logs_created", "user_id", "created_at"),
    )
