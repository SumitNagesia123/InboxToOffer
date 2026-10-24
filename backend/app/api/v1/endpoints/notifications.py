import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification.notification_service import notification_service

router = APIRouter()


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List user notifications",
    description="Retrieves a paginated list of in-app notifications with total unread count.",
)
def list_notifications(
    pagination: Pagination = Depends(),
    is_read: Optional[bool] = Query(None, description="Filter by read or unread status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists notifications for current authenticated user."""
    return notification_service.list_notifications(
        db=db,
        user=current_user,
        is_read=is_read,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    description="Returns the total number of unread notifications for badge indicators.",
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns unread count for badge."""
    count = notification_service.get_unread_count(db=db, user=current_user)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    description="Marks a specific notification as read.",
)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks single notification as read."""
    return notification_service.mark_as_read(
        db=db, user=current_user, notification_id=notification_id
    )


@router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
    description="Marks all unread notifications for the user as read.",
)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks all notifications as read."""
    count = notification_service.mark_all_as_read(db=db, user=current_user)
    return {"success": True, "marked_read": count}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Removes an in-app notification.",
)
def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes notification."""
    notification_service.delete_notification(
        db=db, user=current_user, notification_id=notification_id
    )
    return None
