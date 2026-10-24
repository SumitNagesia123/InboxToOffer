import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationCategory(str, Enum):
    INFO = "INFO"
    MATCH = "MATCH"
    INTERVIEW = "INTERVIEW"
    DIGEST = "DIGEST"
    SYSTEM = "SYSTEM"


class NotificationCreate(BaseModel):
    """Schema for internal notification creation."""
    title: str = Field(..., max_length=255)
    message: str
    category: NotificationCategory = Field(NotificationCategory.INFO)


class NotificationResponse(BaseModel):
    """Public representation of an in-app notification."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    category: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with unread count."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class UnreadCountResponse(BaseModel):
    """Current count of unread notifications for navigation badges."""
    unread_count: int
