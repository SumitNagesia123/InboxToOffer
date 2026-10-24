from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.digest import UserPreferenceResponse, UserPreferenceUpdate
from app.services.digest.digest_service import digest_service

router = APIRouter()


@router.get(
    "",
    response_model=UserPreferenceResponse,
    summary="Get user job search and digest settings",
    description="Retrieves the current user's preferences, digest schedule, and filtering criteria.",
)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves user settings."""
    pref = digest_service.get_or_create_user_preferences(db=db, user=current_user)
    return UserPreferenceResponse.model_validate(pref)


@router.patch(
    "",
    response_model=UserPreferenceResponse,
    summary="Update user job search and digest settings",
    description="Updates user preferences including digest enabled toggle, target time, work modes, and salary thresholds.",
)
def update_user_settings(
    data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates user settings."""
    return digest_service.update_user_preferences(
        db=db, user=current_user, data=data
    )
