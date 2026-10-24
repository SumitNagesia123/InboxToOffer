import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.models.application import Application
from app.models.job import Job
from app.models.match import JobMatch
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationJobSummary,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationUpdate,
    PipelineSummaryResponse,
)


class ApplicationService:
    """Manages candidate job application pipeline stages, updates, and metrics."""

    ALL_STATUSES = [
        ApplicationStatus.DISCOVERED.value,
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.NOT_APPLIED.value,
        ApplicationStatus.INTERVIEWING.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.OFFER.value,
        ApplicationStatus.WITHDRAWN.value,
    ]

    ACTIVE_STATUSES = [
        ApplicationStatus.APPLIED.value,
        ApplicationStatus.INTERVIEWING.value,
        ApplicationStatus.OFFER.value,
    ]

    def _build_response(
        self, application: Application, match_score: Optional[float] = None
    ) -> ApplicationResponse:
        """Constructs an ApplicationResponse with nested job summary and match score."""
        job_summary = None
        if application.job:
            job_summary = ApplicationJobSummary(
                id=application.job.id,
                company_name=application.job.company_name,
                title=application.job.title,
                location=application.job.location,
                work_mode=application.job.work_mode,
                employment_type=application.job.employment_type,
                salary_currency=application.job.salary_currency,
                salary_min=application.job.salary_min,
                salary_max=application.job.salary_max,
                job_url=application.job.job_url,
                platform_source=application.job.platform_source,
            )

        return ApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            job_id=application.job_id,
            status=ApplicationStatus(application.status),
            applied_date=application.applied_date,
            notes=application.notes,
            created_at=application.created_at,
            updated_at=application.updated_at,
            job=job_summary,
            match_score=match_score,
        )

    def create_or_update_application(
        self, db: Session, user: User, data: ApplicationCreate
    ) -> ApplicationResponse:
        """Tracks a new job application or updates an existing one for the same job."""
        # 1. Verify job exists and belongs to the user
        job = db.scalar(
            select(Job).where(Job.id == data.job_id, Job.user_id == user.id)
        )
        if not job:
            raise NotFoundError(message=f"Job with ID {data.job_id} not found for user", code="JOB_NOT_FOUND")

        # 2. Check for existing application
        application = db.scalar(
            select(Application)
            .options(joinedload(Application.job))
            .where(
                Application.user_id == user.id,
                Application.job_id == data.job_id,
            )
        )

        applied_date = data.applied_date
        if data.status == ApplicationStatus.APPLIED and not applied_date:
            applied_date = datetime.now(timezone.utc)

        if application:
            # Update existing application
            application.status = data.status.value
            if data.status == ApplicationStatus.NOT_APPLIED:
                application.applied_date = None
            elif applied_date:
                application.applied_date = applied_date
            if data.notes is not None:
                application.notes = data.notes
            logger.info("Updated existing application %s for user %s", str(application.id), str(user.id))
        else:
            # Create new application
            application = Application(
                user_id=user.id,
                job_id=data.job_id,
                status=data.status.value,
                applied_date=applied_date,
                notes=data.notes,
            )
            db.add(application)
            logger.info("Created new application for job %s and user %s", str(data.job_id), str(user.id))

        db.commit()
        db.refresh(application)

        # Lookup match score if computed
        match_score = db.scalar(
            select(JobMatch.overall_match_score).where(
                JobMatch.user_id == user.id, JobMatch.job_id == data.job_id
            )
        )

        return self._build_response(application, match_score)

    def update_application(
        self, db: Session, user: User, application_id: uuid.UUID, data: ApplicationUpdate
    ) -> ApplicationResponse:
        """Updates status, applied date, or notes on an existing tracked application."""
        application = db.scalar(
            select(Application)
            .options(joinedload(Application.job))
            .where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if not application:
            raise NotFoundError(
                message=f"Application with ID {application_id} not found",
                code="APPLICATION_NOT_FOUND",
            )

        if data.status is not None:
            # If moving to APPLIED and no date is set, auto-set applied_date
            if (
                data.status == ApplicationStatus.APPLIED
                and not application.applied_date
                and not data.applied_date
            ):
                application.applied_date = datetime.now(timezone.utc)
            elif data.status == ApplicationStatus.NOT_APPLIED and not data.applied_date:
                application.applied_date = None
            application.status = data.status.value

        if data.applied_date is not None:
            application.applied_date = data.applied_date

        if data.notes is not None:
            application.notes = data.notes

        db.commit()
        db.refresh(application)

        match_score = db.scalar(
            select(JobMatch.overall_match_score).where(
                JobMatch.user_id == user.id, JobMatch.job_id == application.job_id
            )
        )

        return self._build_response(application, match_score)

    def get_application(
        self, db: Session, user: User, application_id: uuid.UUID
    ) -> ApplicationResponse:
        """Retrieves details of a specific application with job details and match score."""
        application = db.scalar(
            select(Application)
            .options(joinedload(Application.job))
            .where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if not application:
            raise NotFoundError(
                message=f"Application with ID {application_id} not found",
                code="APPLICATION_NOT_FOUND",
            )

        match_score = db.scalar(
            select(JobMatch.overall_match_score).where(
                JobMatch.user_id == user.id, JobMatch.job_id == application.job_id
            )
        )

        return self._build_response(application, match_score)

    def list_applications(
        self,
        db: Session,
        user: User,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> ApplicationListResponse:
        """Lists applications with optional filtering by status and search terms."""
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .join(Job, Application.job_id == Job.id)
            .where(Application.user_id == user.id)
        )

        if status:
            statuses = [s.strip().upper() for s in status.split(",") if s.strip()]
            valid_statuses = [s for s in statuses if s in self.ALL_STATUSES]
            if valid_statuses:
                stmt = stmt.where(Application.status.in_(valid_statuses))

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                Job.title.ilike(search_pattern) | Job.company_name.ilike(search_pattern)
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sort
        sort_col = getattr(Application, sort_by, Application.updated_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_col.asc())
        else:
            stmt = stmt.order_by(sort_col.desc())

        stmt = stmt.offset(skip).limit(limit)
        applications = db.scalars(stmt).unique().all()

        # Batch lookup match scores for all fetched jobs
        job_ids = [app.job_id for app in applications]
        match_scores_map: Dict[uuid.UUID, float] = {}
        if job_ids:
            matches = db.execute(
                select(JobMatch.job_id, JobMatch.overall_match_score).where(
                    JobMatch.user_id == user.id, JobMatch.job_id.in_(job_ids)
                )
            ).all()
            for j_id, score in matches:
                match_scores_map[j_id] = score

        items = [
            self._build_response(app, match_scores_map.get(app.job_id))
            for app in applications
        ]

        return ApplicationListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_pipeline_summary(self, db: Session, user: User) -> PipelineSummaryResponse:
        """Calculates stage counts, active applications, and conversion percentages."""
        counts = db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user.id)
            .group_by(Application.status)
        ).all()

        stage_counts = {st: 0 for st in self.ALL_STATUSES}
        for st, count in counts:
            if st in stage_counts:
                stage_counts[st] = count

        total_applications = sum(stage_counts.values())
        active_count = (
            stage_counts[ApplicationStatus.APPLIED.value]
            + stage_counts[ApplicationStatus.INTERVIEWING.value]
            + stage_counts[ApplicationStatus.OFFER.value]
        )

        applied_base = (
            stage_counts[ApplicationStatus.APPLIED.value]
            + stage_counts[ApplicationStatus.INTERVIEWING.value]
            + stage_counts[ApplicationStatus.OFFER.value]
            + stage_counts[ApplicationStatus.REJECTED.value]
        )

        interview_rate = 0.0
        offer_rate = 0.0
        if applied_base > 0:
            interviewing_or_beyond = (
                stage_counts[ApplicationStatus.INTERVIEWING.value]
                + stage_counts[ApplicationStatus.OFFER.value]
            )
            interview_rate = round((interviewing_or_beyond / applied_base) * 100.0, 1)
            offer_rate = round((stage_counts[ApplicationStatus.OFFER.value] / applied_base) * 100.0, 1)

        return PipelineSummaryResponse(
            total_applications=total_applications,
            stage_counts=stage_counts,
            active_count=active_count,
            interview_rate_percentage=interview_rate,
            offer_rate_percentage=offer_rate,
        )

    def delete_application(self, db: Session, user: User, application_id: uuid.UUID) -> None:
        """Removes a tracked application."""
        application = db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if not application:
            raise NotFoundError(
                message=f"Application with ID {application_id} not found",
                code="APPLICATION_NOT_FOUND",
            )

        db.delete(application)
        db.commit()
        logger.info("Deleted application %s for user %s", str(application_id), str(user.id))

    def sync_status_from_email_event(
        self,
        db: Session,
        user: User,
        company_name: str,
        event_category: str,
    ) -> Optional[ApplicationResponse]:
        """Automatically transitions application status when interview or offer emails arrive."""
        target_status = None
        event_clean = event_category.upper()
        if "INTERVIEW" in event_clean:
            target_status = ApplicationStatus.INTERVIEWING
        elif "OFFER" in event_clean:
            target_status = ApplicationStatus.OFFER
        elif "REJECTION" in event_clean:
            target_status = ApplicationStatus.REJECTED

        if not target_status:
            return None

        # Find matching application for this user and company
        app = db.scalar(
            select(Application)
            .options(joinedload(Application.job))
            .join(Job, Application.job_id == Job.id)
            .where(
                Application.user_id == user.id,
                Job.company_name.ilike(company_name.strip()),
                Application.status.in_([
                    ApplicationStatus.DISCOVERED.value,
                    ApplicationStatus.APPLIED.value,
                    ApplicationStatus.INTERVIEWING.value,
                ]),
            )
            .order_by(Application.updated_at.desc())
        )

        if not app:
            return None

        app.status = target_status.value
        note_append = f"Auto-updated to {target_status.value} from incoming {event_category} email."
        if app.notes:
            app.notes += f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {note_append}"
        else:
            app.notes = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {note_append}"

        db.commit()
        db.refresh(app)
        logger.info("Auto-transitioned application %s to %s for company %s", str(app.id), target_status.value, company_name)
        return self._build_response(app)


application_service = ApplicationService()
