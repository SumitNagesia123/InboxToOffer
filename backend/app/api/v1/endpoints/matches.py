import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models.user import User
from app.schemas.match import (
    BatchMatchResponse,
    JobMatchResponse,
    MatchListResponse,
)
from app.services.matching.matching_service import matching_service

router = APIRouter()


@router.post(
    "/compute-all",
    response_model=BatchMatchResponse,
    summary="Compute matches for all jobs",
    description="Evaluates all active canonical jobs against the user's active resume profile.",
)
def compute_all_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes batch matching evaluation across all candidate jobs."""
    return matching_service.batch_match_all_jobs(db=db, user=current_user)


@router.post(
    "/compute/{job_id}",
    response_model=JobMatchResponse,
    summary="Compute match for a single job",
    description="Calculates detailed explainable match score breakdown for a specific job.",
)
def compute_single_match(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Computes and stores compatibility analysis for specified job."""
    return matching_service.match_job_for_user(
        db=db,
        user=current_user,
        job_id=job_id,
    )


@router.get(
    "",
    response_model=MatchListResponse,
    summary="List job matches",
    description="Retrieves a paginated list of job matches ordered by match score from highest to lowest.",
)
def list_job_matches(
    pagination: Pagination = Depends(),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Filter matches by minimum overall score percentage"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns ranked list of candidate job matches."""
    return matching_service.list_matches(
        db=db,
        user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        min_score=min_score,
    )


@router.get(
    "/{job_id}",
    response_model=JobMatchResponse,
    summary="Get match breakdown for a job",
    description="Retrieves explainable match metrics, skill gaps, and alignment summary for a specific job.",
)
def get_match_breakdown(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves or calculates match breakdown for specified job."""
    return matching_service.get_match_detail(
        db=db,
        user=current_user,
        job_id=job_id,
    )
