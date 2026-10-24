import uuid
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.audit import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationCategory,
    NotificationListResponse,
    NotificationResponse,
)


class NotificationService:
    """Manages creation, retrieval, and status of in-app user notifications."""

    def create_notification(
        self,
        db: Session,
        user_id: uuid.UUID,
        title: str,
        message: str,
        category: str = NotificationCategory.INFO.value,
    ) -> Notification:
        """Emits an in-app notification for the target user."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            is_read=False,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info("Notification created for user %s: [%s] %s", str(user_id), category, title)
        return notification

    def list_notifications(
        self,
        db: Session,
        user: User,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> NotificationListResponse:
        """Retrieves paginated notifications for the authenticated user."""
        stmt = select(Notification).where(Notification.user_id == user.id)

        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Unread count total
        unread_count_stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
        unread_count = db.scalar(unread_count_stmt) or 0

        # Retrieve items sorted by creation descending
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        items = db.scalars(stmt).all()

        return NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in items],
            total=total,
            unread_count=unread_count,
            skip=skip,
            limit=limit,
        )

    def get_unread_count(self, db: Session, user: User) -> int:
        """Returns the number of unread notifications for navigation badges."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
        return db.scalar(stmt) or 0

    def mark_as_read(
        self, db: Session, user: User, notification_id: uuid.UUID
    ) -> NotificationResponse:
        """Marks a specific notification as read."""
        notification = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
        if not notification:
            raise NotFoundError(
                message=f"Notification with ID {notification_id} not found",
                code="NOTIFICATION_NOT_FOUND",
            )

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return NotificationResponse.model_validate(notification)

    def mark_all_as_read(self, db: Session, user: User) -> int:
        """Marks all unread notifications as read for the user."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        result = db.execute(stmt)
        db.commit()
        updated_count = result.rowcount
        logger.info("Marked %d notifications as read for user %s", updated_count, str(user.id))
        return updated_count

    def delete_notification(
        self, db: Session, user: User, notification_id: uuid.UUID
    ) -> None:
        """Deletes a notification record."""
        notification = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
        if not notification:
            raise NotFoundError(
                message=f"Notification with ID {notification_id} not found",
                code="NOTIFICATION_NOT_FOUND",
            )

        db.delete(notification)
        db.commit()
        logger.info("Deleted notification %s for user %s", str(notification_id), str(user.id))


notification_service = NotificationService()
