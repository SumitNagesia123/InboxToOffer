import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.job import Job
from app.models.user import User
from app.schemas.job import (
    BatchDeduplicationResponse,
    BatchExtractionResponse,
    DuplicateGroupResponse,
    DuplicateMatchDetail,
    JobListResponse,
    JobResponse,
)
from app.services.job.deduplication_service import job_deduplication_service
from app.services.job.extraction_service import job_extraction_service
from app.services.email.ingestion_service import email_ingestion_service

router = APIRouter()


@router.post(
    "/extract/{email_id}",
    response_model=JobResponse,
    summary="Extract structured job from email",
    description="Parses structured job details (title, company, salary, experience, skills) from a specified email.",
)
def extract_job_from_email(
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract and persist structured job posting from an email."""
    from app.models.email import Email
    email = db.get(Email, email_id)
    if not email or email.user_id != current_user.id:
        raise NotFoundError(f"Email with ID '{email_id}' was not found.")

    job = job_extraction_service.extract_and_store_job(
        db=db,
        user=current_user,
        email=email,
    )
    return job_extraction_service.get_job(db=db, user=current_user, job_id=job.id)


@router.post(
    "/extract-all",
    response_model=BatchExtractionResponse,
    summary="Batch extract jobs from all pending job emails",
    description="Finds all classified job emails and extracts structured job entities into the database.",
)
def extract_all_jobs(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch extract structured jobs from job emails."""
    return job_extraction_service.extract_from_classified_emails(
        db=db,
        user=current_user,
        limit=limit,
    )


@router.post(
    "/deduplicate",
    response_model=BatchDeduplicationResponse,
    summary="Batch deduplicate user jobs",
    description="Performs a full sweep across user jobs detecting and clustering duplicates by URL, fingerprint, and content similarity.",
)
def deduplicate_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes duplicate detection sweep over all user jobs."""
    return job_deduplication_service.deduplicate_user_jobs(
        db=db,
        user=current_user,
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List extracted jobs",
    description="Returns a paginated list of extracted structured jobs with search, filtering, and duplicate visibility toggles.",
)
def list_jobs(
    pagination: Pagination = Depends(),
    search: Optional[str] = Query(None, description="Search term for title or company"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode: REMOTE, HYBRID, ON_SITE"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    include_duplicates: bool = Query(False, description="Whether to include duplicate job postings in results"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List extracted jobs for authenticated user."""
    return job_extraction_service.list_jobs(
        db=db,
        user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        search=search,
        work_mode=work_mode,
        company=company,
        include_duplicates=include_duplicates,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Retrieves full structured job information including required/preferred skills.",
)
def get_job_detail(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single job details by ID."""
    return job_extraction_service.get_job(
        db=db,
        user=current_user,
        job_id=job_id,
    )


@router.post(
    "/{job_id}/check-duplicate",
    response_model=DuplicateMatchDetail,
    summary="Check duplicate status for a job",
    description="Analyzes whether a specific job matches existing canonical jobs.",
)
def check_job_duplicate(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Explicitly triggers duplicate evaluation for a job."""
    job = db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError(f"Job with ID '{job_id}' was not found.")

    return job_deduplication_service.check_and_link_duplicate(
        db=db,
        job=job,
    )


@router.get(
    "/{job_id}/duplicates",
    response_model=DuplicateGroupResponse,
    summary="Get duplicate cluster for a canonical job",
    description="Retrieves a canonical job alongside all duplicate postings linked to it.",
)
def get_job_duplicates(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gets canonical job and its linked duplicate postings."""
    return job_deduplication_service.get_duplicate_group(
        db=db,
        user=current_user,
        canonical_job_id=job_id,
    )
