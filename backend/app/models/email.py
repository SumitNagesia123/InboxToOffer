import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job import Job


class Email(Base, UUIDPrimaryKeyMixin):
    """Raw and processed email ingested from Gmail API."""
    __tablename__ = "emails"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    gmail_message_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Classification & Processing Status
    category: Mapped[str] = mapped_column(String(50), default="OTHER", index=True, nullable=False)
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="emails")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="source_email")

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_user_gmail_msg"),
        Index("idx_emails_user_status", "user_id", "processed_status"),
        Index("idx_emails_user_category", "user_id", "category"),
    )
