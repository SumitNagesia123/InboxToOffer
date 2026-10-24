import uuid
from typing import Generator, Optional
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


class Pagination:
    """Reusable pagination dependency."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(50, ge=1, le=500, description="Max number of items to return"),
    ):
        self.skip = skip
        self.limit = limit


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the JWT Bearer token, returning the authenticated User."""
    if not token:
        raise AuthenticationError("Authentication token is missing. Please log in.")

    payload = decode_access_token(token)
    user_id_str = payload.get("sub")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Malformed user identifier in token")

    user = db.get(User, user_uuid)
    if not user:
        raise AuthenticationError("User associated with this token does not exist")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency ensuring the authenticated user has superuser privileges."""
    if not current_user.is_superuser:
        raise PermissionDeniedError("Administrative privileges required")
    return current_user


__all__ = [
    "get_db",
    "Pagination",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_superuser",
]
