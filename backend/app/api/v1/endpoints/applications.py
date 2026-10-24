import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
    PipelineSummaryResponse,
)
from app.services.application.application_service import application_service

router = APIRouter()


@router.get(
    "/pipeline/summary",
    response_model=PipelineSummaryResponse,
    summary="Get application pipeline summary",
    description="Returns aggregate stage counts, active applications, and interview/offer conversion rates.",
)
def get_pipeline_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provides pipeline stage metrics for dashboard and Kanban view."""
    return application_service.get_pipeline_summary(db=db, user=current_user)


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List tracked job applications",
    description="Retrieves a paginated list of job applications with optional status and search filtering.",
)
def list_applications(
    pagination: Pagination = Depends(),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status (e.g. 'APPLIED' or comma-separated 'APPLIED,INTERVIEWING')",
    ),
    search: Optional[str] = Query(
        None,
        description="Search across job title and company name",
    ),
    sort_by: str = Query("updated_at", description="Field to sort by (updated_at, applied_date, created_at)"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction (asc or desc)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves paginated applications for the current authenticated user."""
    return application_service.list_applications(
        db=db,
        user=current_user,
        status=status_filter,
        search=search,
        skip=pagination.skip,
        limit=pagination.limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track new job application",
    description="Creates a new application entry or updates an existing tracked application for the specified job.",
)
def track_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tracks a job application in the candidate's personal pipeline."""
    return application_service.create_or_update_application(
        db=db, user=current_user, data=data
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get application details",
    description="Retrieves full details of a tracked job application including embedded job summary and match score.",
)
def get_application_details(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches a specific application by ID."""
    return application_service.get_application(
        db=db, user=current_user, application_id=application_id
    )


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update application status or notes",
    description="Updates the pipeline status, application submission date, or notes on an existing tracked application.",
)
def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates pipeline stage or notes for a tracked application."""
    return application_service.update_application(
        db=db, user=current_user, application_id=application_id, data=data
    )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tracked application",
    description="Removes a job application from the candidate's personal tracking pipeline.",
)
def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes an application entry."""
    application_service.delete_application(
        db=db, user=current_user, application_id=application_id
    )
    return None
