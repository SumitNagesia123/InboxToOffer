import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ProcessingRun(Base, UUIDPrimaryKeyMixin):
    """Audit log of pipeline and sync execution cycles."""
    __tablename__ = "processing_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)  # RUNNING, COMPLETED, FAILED
    emails_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="processing_runs")


class ProcessingError(Base, UUIDPrimaryKeyMixin):
    """Detailed error log for debugging ingestion or NLP failures."""
    __tablename__ = "processing_errors"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(String(100), nullable=False)  # GMAIL_SYNC, CLASSIFICATION, EXTRACTION, etc.
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_email_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Notification(Base, UUIDPrimaryKeyMixin):
    """User notifications for important events (new high-match jobs, interview invitations)."""
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="INFO", nullable=False)  # MATCH, INTERVIEW, SYSTEM
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DailyDigest(Base, UUIDPrimaryKeyMixin):
    """Record of sent daily job digests."""
    __tablename__ = "daily_digests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    total_emails_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top_matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SENT", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="daily_digests")
