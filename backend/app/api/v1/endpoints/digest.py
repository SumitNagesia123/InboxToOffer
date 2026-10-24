from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models.user import User
from app.schemas.digest import (
    DailyDigestListResponse,
    DigestPreviewResponse,
    TriggerDigestResponse,
    UserPreferenceResponse,
    UserPreferenceUpdate,
)
from app.services.digest.digest_service import digest_service

router = APIRouter()


@router.post(
    "/trigger",
    response_model=TriggerDigestResponse,
    summary="Trigger daily digest dispatch",
    description="Manually generates, compiles, and dispatches the daily job digest email.",
)
def trigger_digest(
    force: bool = Query(False, description="Force delivery even if digest is toggled off in preferences"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers an on-demand daily digest dispatch."""
    return digest_service.dispatch_digest_for_user(
        db=db, user=current_user, force=force
    )


@router.get(
    "/preview",
    response_model=DigestPreviewResponse,
    summary="Preview today's digest",
    description="Generates and previews today's job digest content and HTML without sending an email.",
)
def preview_digest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates preview payload with HTML and text renderings."""
    return digest_service.generate_digest_content(db=db, user=current_user)


@router.get(
    "/history",
    response_model=DailyDigestListResponse,
    summary="Get digest dispatch history",
    description="Lists past sent daily digests with delivery statistics.",
)
def get_digest_history(
    pagination: Pagination = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves paginated digest dispatch records."""
    return digest_service.list_digest_history(
        db=db, user=current_user, skip=pagination.skip, limit=pagination.limit
    )


@router.get(
    "/preferences",
    response_model=UserPreferenceResponse,
    summary="Get digest preferences",
    description="Retrieves the user's daily digest schedule, modality filters, and salary thresholds.",
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns current user digest preferences."""
    pref = digest_service.get_or_create_user_preferences(db=db, user=current_user)
    return UserPreferenceResponse.model_validate(pref)


@router.patch(
    "/preferences",
    response_model=UserPreferenceResponse,
    summary="Update digest preferences",
    description="Updates the user's daily digest schedule, modality filters, or minimum salary.",
)
def update_preferences(
    data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates user digest preferences."""
    return digest_service.update_user_preferences(
        db=db, user=current_user, data=data
    )
