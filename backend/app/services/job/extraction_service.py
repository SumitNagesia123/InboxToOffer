import re
import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.company import Company
from app.models.email import Email
from app.models.job import Job, JobSkill
from app.models.skill import Skill
from app.models.user import User
from app.schemas.job import (
    BatchExtractionResponse,
    ExtractedJobData,
    JobListResponse,
    JobResponse,
)
from app.services.nlp.extractor import job_extractor


def _normalize_name(name: str) -> str:
    """Normalizes string for unique lookup (lowercase, alphanumeric + underscore)."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")


class JobExtractionService:
    """Orchestrates structured job parsing, company/skill entity linking, and database persistence."""

    def _get_or_create_company(self, db: Session, company_name: str) -> Company:
        """Finds or creates normalized Company master record."""
        norm_name = _normalize_name(company_name) or "unknown_company"
        company = db.scalar(select(Company).where(Company.normalized_name == norm_name))
        if not company:
            company = Company(
                name=company_name,
                normalized_name=norm_name,
            )
            db.add(company)
            db.flush()
        return company

    def _get_or_create_skill(self, db: Session, skill_name: str) -> Skill:
        """Finds or creates normalized Skill taxonomy record."""
        norm_name = _normalize_name(skill_name)
        skill = db.scalar(select(Skill).where(Skill.normalized_name == norm_name))
        if not skill:
            skill = Skill(
                name=skill_name,
                normalized_name=norm_name,
            )
            db.add(skill)
            db.flush()
        return skill

    def extract_and_store_job(self, db: Session, user: User, email: Email) -> Job:
        """Extracts structured information from email and persists Job and JobSkills."""
        data: ExtractedJobData = job_extractor.extract(
            subject=email.subject,
            sender=email.sender,
            body=email.body_text or "",
            body_html=email.body_html,
        )

        company = self._get_or_create_company(db, data.company_name)
        normalized_title = data.title.lower().strip()

        job = Job(
            user_id=user.id,
            source_email_id=email.id,
            company_id=company.id,
            company_name=data.company_name,
            title=data.title,
            normalized_title=normalized_title,
            location=data.location,
            work_mode=data.work_mode.value,
            employment_type=data.employment_type.value,
            salary_currency=data.salary_currency,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            min_experience_years=data.min_experience_years,
            max_experience_years=data.max_experience_years,
            job_description=data.job_description,
            job_url=data.job_url,
            platform_source=data.platform_source,
            application_deadline=data.application_deadline,
            is_duplicate=False,
        )
        db.add(job)
        db.flush()  # Populates job.id

        # Link required skills
        for skill_name in data.required_skills:
            skill_obj = self._get_or_create_skill(db, skill_name)
            job_skill = JobSkill(job_id=job.id, skill_id=skill_obj.id, is_required=True)
            db.add(job_skill)

        # Link preferred skills
        for skill_name in data.preferred_skills:
            skill_obj = self._get_or_create_skill(db, skill_name)
            job_skill = JobSkill(job_id=job.id, skill_id=skill_obj.id, is_required=False)
            db.add(job_skill)

        email.processed_status = "EXTRACTED"
        db.commit()
        db.refresh(job)

        # Check for duplicates across user's existing jobs
        from app.services.job.deduplication_service import job_deduplication_service
        job_deduplication_service.check_and_link_duplicate(db=db, job=job)

        logger.info("Successfully extracted and saved job '%s' at '%s' for user %s", job.title, job.company_name, str(user.id))
        return job

    def extract_from_classified_emails(self, db: Session, user: User, limit: int = 50) -> BatchExtractionResponse:
        """Finds job-related emails and runs structured extraction."""
        candidate_emails = db.scalars(
            select(Email)
            .where(
                Email.user_id == user.id,
                Email.category.in_(["JOB", "JOB_ALERT"]),
                Email.processed_status.in_(["PENDING", "CLASSIFIED"]),
            )
            .limit(limit)
        ).all()

        extracted_count = 0
        for email in candidate_emails:
            try:
                self.extract_and_store_job(db=db, user=user, email=email)
                extracted_count += 1
            except Exception as e:
                logger.error("Error extracting job from email %s: %s", str(email.id), str(e))

        return BatchExtractionResponse(
            total_processed=len(candidate_emails),
            jobs_extracted=extracted_count,
            message=f"Batch job extraction complete: {extracted_count} jobs created from {len(candidate_emails)} emails.",
        )

    def list_jobs(
        self,
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        work_mode: Optional[str] = None,
        company: Optional[str] = None,
        include_duplicates: bool = False,
    ) -> JobListResponse:
        """Returns paginated extracted jobs for current user."""
        query = select(Job).where(Job.user_id == user.id)

        if not include_duplicates:
            query = query.where(Job.is_duplicate.is_(False))
        if work_mode:
            query = query.where(Job.work_mode == work_mode.upper())
        if company:
            query = query.where(Job.company_name.ilike(f"%{company.strip()}%"))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where((Job.title.ilike(pattern)) | (Job.company_name.ilike(pattern)))

        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        jobs = db.scalars(
            query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        ).all()

        items: List[JobResponse] = []
        for j in jobs:
            req_skills = [js.skill.name for js in j.job_skills if js.is_required and js.skill]
            pref_skills = [js.skill.name for js in j.job_skills if not js.is_required and js.skill]
            items.append(
                JobResponse(
                    id=j.id,
                    user_id=j.user_id,
                    source_email_id=j.source_email_id,
                    company_id=j.company_id,
                    company_name=j.company_name,
                    title=j.title,
                    normalized_title=j.normalized_title,
                    location=j.location,
                    work_mode=j.work_mode,
                    employment_type=j.employment_type,
                    salary_currency=j.salary_currency,
                    salary_min=j.salary_min,
                    salary_max=j.salary_max,
                    min_experience_years=j.min_experience_years,
                    max_experience_years=j.max_experience_years,
                    job_description=j.job_description,
                    job_url=j.job_url,
                    platform_source=j.platform_source,
                    posted_date=j.posted_date,
                    application_deadline=j.application_deadline,
                    is_duplicate=j.is_duplicate,
                    canonical_job_id=j.canonical_job_id,
                    required_skills=req_skills,
                    preferred_skills=pref_skills,
                    created_at=j.created_at,
                )
            )

        return JobListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_job(self, db: Session, user: User, job_id: uuid.UUID) -> JobResponse:
        """Retrieves single job detail with skill lists."""
        job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
        if not job:
            raise NotFoundError(f"Job with ID '{job_id}' not found.")

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


job_extraction_service = JobExtractionService()
