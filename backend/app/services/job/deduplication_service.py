import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.job import Job, JobSkill
from app.models.user import User
from app.schemas.job import (
    BatchDeduplicationResponse,
    DuplicateGroupResponse,
    DuplicateMatchDetail,
    JobResponse,
)
from app.services.job.deduplication_engine import deduplication_engine


class JobDeduplicationService:
    """Manages duplicate detection, canonical job clustering, and metadata enrichment."""

    @staticmethod
    def _to_job_response(job: Job) -> JobResponse:
        """Helper to serialize a Job model into a JobResponse schema."""
        req_skills = [js.skill.name for js in job.job_skills if js.is_required and js.skill]
        pref_skills = [js.skill.name for js in job.job_skills if not js.is_required and js.skill]
        return JobResponse(
            id=job.id,
            user_id=job.user_id,
            source_email_id=job.source_email_id,
            company_id=job.company_id,
            company_name=job.company_name,
            title=job.title,
            normalized_title=job.normalized_title,
            location=job.location,
            work_mode=job.work_mode,
            employment_type=job.employment_type,
            salary_currency=job.salary_currency,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            min_experience_years=job.min_experience_years,
            max_experience_years=job.max_experience_years,
            job_description=job.job_description,
            job_url=job.job_url,
            platform_source=job.platform_source,
            posted_date=job.posted_date,
            application_deadline=job.application_deadline,
            is_duplicate=job.is_duplicate,
            canonical_job_id=job.canonical_job_id,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            created_at=job.created_at,
        )

    def enrich_canonical_job(self, canonical: Job, duplicate: Job) -> bool:
        """Enriches canonical job with any missing details present in duplicate posting."""
        enriched = False
        if not canonical.salary_min and duplicate.salary_min:
            canonical.salary_currency = duplicate.salary_currency
            canonical.salary_min = duplicate.salary_min
            canonical.salary_max = duplicate.salary_max
            enriched = True

        if not canonical.min_experience_years and duplicate.min_experience_years:
            canonical.min_experience_years = duplicate.min_experience_years
            canonical.max_experience_years = duplicate.max_experience_years
            enriched = True

        if not canonical.job_url and duplicate.job_url:
            canonical.job_url = duplicate.job_url
            enriched = True

        if not canonical.location and duplicate.location:
            canonical.location = duplicate.location
            enriched = True

        if not canonical.application_deadline and duplicate.application_deadline:
            canonical.application_deadline = duplicate.application_deadline
            enriched = True

        return enriched

    def check_and_link_duplicate(self, db: Session, job: Job) -> DuplicateMatchDetail:
        """Checks newly created or specified job against existing canonical jobs for current user."""
        # Query existing canonical jobs for this user
        existing_canonical_jobs = db.scalars(
            select(Job).where(
                Job.user_id == job.user_id,
                Job.id != job.id,
                Job.is_duplicate.is_(False),
            ).order_by(Job.created_at.asc())
        ).all()

        for canonical in existing_canonical_jobs:
            match = deduplication_engine.compare_jobs(
                candidate_url=job.job_url,
                candidate_company=job.company_name,
                candidate_title=job.title,
                candidate_description=job.job_description,
                candidate_location=job.location,
                existing_url=canonical.job_url,
                existing_company=canonical.company_name,
                existing_title=canonical.title,
                existing_description=canonical.job_description,
                existing_location=canonical.location,
            )

            if match.is_duplicate:
                job.is_duplicate = True
                job.canonical_job_id = canonical.id
                match.canonical_job_id = canonical.id

                # Enrich canonical job if duplicate contains missing data
                self.enrich_canonical_job(canonical, job)

                db.commit()
                db.refresh(job)
                db.refresh(canonical)
                logger.info(
                    "Job %s ('%s' at '%s') detected as duplicate of %s via %s (conf: %.2f)",
                    str(job.id), job.title, job.company_name, str(canonical.id),
                    match.match_method, match.confidence,
                )
                return match

        # Not a duplicate
        return DuplicateMatchDetail(
            is_duplicate=False,
            confidence=0.0,
            match_method=None,
            reasons=[],
            canonical_job_id=None,
        )

    def deduplicate_user_jobs(self, db: Session, user: User) -> BatchDeduplicationResponse:
        """Runs a complete deduplication sweep across all jobs belonging to the specified user."""
        all_jobs = db.scalars(
            select(Job).where(Job.user_id == user.id).order_by(Job.created_at.asc())
        ).all()

        if not all_jobs:
            return BatchDeduplicationResponse(
                total_jobs=0,
                duplicates_identified=0,
                unique_canonical_jobs=0,
                message="No jobs found for user.",
            )

        canonical_pool: List[Job] = []
        duplicates_count = 0

        for current_job in all_jobs:
            found_duplicate = False
            for canonical in canonical_pool:
                match = deduplication_engine.compare_jobs(
                    candidate_url=current_job.job_url,
                    candidate_company=current_job.company_name,
                    candidate_title=current_job.title,
                    candidate_description=current_job.job_description,
                    candidate_location=current_job.location,
                    existing_url=canonical.job_url,
                    existing_company=canonical.company_name,
                    existing_title=canonical.title,
                    existing_description=canonical.job_description,
                    existing_location=canonical.location,
                )

                if match.is_duplicate:
                    current_job.is_duplicate = True
                    current_job.canonical_job_id = canonical.id
                    self.enrich_canonical_job(canonical, current_job)
                    duplicates_count += 1
                    found_duplicate = True
                    break

            if not found_duplicate:
                current_job.is_duplicate = False
                current_job.canonical_job_id = None
                canonical_pool.append(current_job)

        db.commit()
        return BatchDeduplicationResponse(
            total_jobs=len(all_jobs),
            duplicates_identified=duplicates_count,
            unique_canonical_jobs=len(canonical_pool),
            message=f"Deduplication complete: {duplicates_count} duplicates linked across {len(all_jobs)} total jobs.",
        )

    def get_duplicate_group(
        self, db: Session, user: User, canonical_job_id: uuid.UUID
    ) -> DuplicateGroupResponse:
        """Retrieves canonical job and all linked duplicate records for authenticated user."""
        canonical_job = db.scalar(
            select(Job).where(Job.id == canonical_job_id, Job.user_id == user.id)
        )
        if not canonical_job:
            raise NotFoundError(f"Job with ID '{canonical_job_id}' was not found.")

        # If this job itself points to a canonical job, resolve to the true canonical root
        root_job = canonical_job
        if canonical_job.canonical_job_id:
            root_job = db.scalar(
                select(Job).where(Job.id == canonical_job.canonical_job_id, Job.user_id == user.id)
            ) or canonical_job

        duplicate_jobs = db.scalars(
            select(Job).where(
                Job.canonical_job_id == root_job.id,
                Job.user_id == user.id,
            ).order_by(Job.created_at.desc())
        ).all()

        return DuplicateGroupResponse(
            canonical_job=self._to_job_response(root_job),
            duplicate_jobs=[self._to_job_response(j) for j in duplicate_jobs],
            duplicate_count=len(duplicate_jobs),
        )


job_deduplication_service = JobDeduplicationService()
