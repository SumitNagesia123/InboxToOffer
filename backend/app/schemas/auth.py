import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for user account registration."""
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name of the user")


class UserLoginRequest(BaseModel):
    """Payload for user account authentication."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserUpdateRequest(BaseModel):
    """Payload for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=255)


class QuickLoginRequest(BaseModel):
    """Payload for quick authentication in local development."""
    email: EmailStr = Field(..., description="Registered email address to authenticate")


class TokenResponse(BaseModel):
    """OAuth2-compatible Bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Public user profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
