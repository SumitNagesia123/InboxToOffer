import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import logger
from app.models.job import Job, JobSkill
from app.models.match import JobMatch
from app.models.resume import Resume, ResumeSkill
from app.models.user import User
from app.schemas.match import (
    BatchMatchResponse,
    JobMatchResponse,
    MatchListResponse,
)
from app.services.matching.matching_engine import MatchEvaluationResult, matching_engine


class MatchingService:
    """Orchestrates job-to-resume compatibility analysis, persistence, and querying."""

    @staticmethod
    def _to_match_response(match: JobMatch) -> JobMatchResponse:
        """Serializes JobMatch database model to JobMatchResponse schema."""
        return JobMatchResponse(
            id=match.id,
            user_id=match.user_id,
            job_id=match.job_id,
            resume_id=match.resume_id,
            job_title=match.job.title if match.job else "Unknown Role",
            company_name=match.job.company_name if match.job else "Unknown Company",
            overall_match_score=match.overall_match_score,
            skill_score=match.skill_score,
            experience_score=match.experience_score,
            semantic_score=match.semantic_score,
            matched_skills=match.matched_skills or [],
            missing_required_skills=match.missing_required_skills or [],
            missing_preferred_skills=match.missing_preferred_skills or [],
            explanation_summary=match.explanation_summary,
            job_url=match.job.job_url if match.job else None,
            source_email_id=match.job.source_email_id if match.job else None,
            created_at=match.created_at,
        )

    def match_job_for_user(self, db: Session, user: User, job_id: uuid.UUID) -> JobMatchResponse:
        """Evaluates compatibility between a specific job and the candidate's active resume."""
        # 1. Fetch active resume
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise ValidationError("You must upload a resume before calculating match scores.")

        # 2. Fetch job record
        job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
        if not job:
            raise NotFoundError(f"Job with ID '{job_id}' was not found.")

        # 3. Collect candidate skills
        candidate_skills = [
            rs.skill.name for rs in resume.resume_skills if rs.skill
        ]

        # 4. Collect job required & preferred skills
        job_req_skills = [
            js.skill.name for js in job.job_skills if js.is_required and js.skill
        ]
        job_pref_skills = [
            js.skill.name for js in job.job_skills if not js.is_required and js.skill
        ]

        # 5. Execute matching engine calculation
        result: MatchEvaluationResult = matching_engine.calculate_match(
            candidate_skills=candidate_skills,
            candidate_years=resume.total_experience_years,
            resume_text=resume.extracted_text,
            job_title=job.title,
            job_description=job.job_description,
            job_min_exp=job.min_experience_years,
            job_max_exp=job.max_experience_years,
            job_required_skills=job_req_skills,
            job_preferred_skills=job_pref_skills,
        )

        # 6. Upsert JobMatch record
        match = db.scalar(
            select(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.job_id == job.id,
                JobMatch.resume_id == resume.id,
            )
        )

        if match:
            match.overall_match_score = result.overall_match_score
            match.skill_score = result.skill_score
            match.experience_score = result.experience_score
            match.semantic_score = result.semantic_score
            match.matched_skills = result.matched_skills
            match.missing_required_skills = result.missing_required_skills
            match.missing_preferred_skills = result.missing_preferred_skills
            match.explanation_summary = result.explanation_summary
        else:
            match = JobMatch(
                user_id=user.id,
                job_id=job.id,
                resume_id=resume.id,
                overall_match_score=result.overall_match_score,
                skill_score=result.skill_score,
                experience_score=result.experience_score,
                semantic_score=result.semantic_score,
                matched_skills=result.matched_skills,
                missing_required_skills=result.missing_required_skills,
                missing_preferred_skills=result.missing_preferred_skills,
                explanation_summary=result.explanation_summary,
            )
            db.add(match)

        db.commit()
        db.refresh(match)
        logger.info(
            "Computed match score %.1f%% for job '%s' (user %s)",
            match.overall_match_score, job.title, str(user.id),
        )
        return self._to_match_response(match)

    def batch_match_all_jobs(self, db: Session, user: User) -> BatchMatchResponse:
        """Runs match analysis across all active canonical jobs for the authenticated user."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise ValidationError("You must upload a resume before calculating match scores.")

        canonical_jobs = db.scalars(
            select(Job).where(
                Job.user_id == user.id,
                Job.is_duplicate.is_(False),
            )
        ).all()

        if not canonical_jobs:
            return BatchMatchResponse(
                total_jobs_evaluated=0,
                total_matches_created=0,
                average_match_score=0.0,
                high_match_count=0,
                message="No jobs found to evaluate.",
            )

        total_score = 0.0
        high_matches = 0
        matches_count = 0

        for job in canonical_jobs:
            try:
                res = self.match_job_for_user(db=db, user=user, job_id=job.id)
                total_score += res.overall_match_score
                if res.overall_match_score >= 70.0:
                    high_matches += 1
                matches_count += 1
            except Exception as e:
                logger.error("Error calculating match for job %s: %s", str(job.id), str(e))

        avg_score = round(total_score / matches_count, 1) if matches_count > 0 else 0.0

        return BatchMatchResponse(
            total_jobs_evaluated=len(canonical_jobs),
            total_matches_created=matches_count,
            average_match_score=avg_score,
            high_match_count=high_matches,
            message=f"Analyzed {matches_count} jobs. Average score: {avg_score}%. {high_matches} strong matches found.",
        )

    def list_matches(
        self,
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 50,
        min_score: Optional[float] = None,
    ) -> MatchListResponse:
        """Returns paginated matches for user ordered from highest score to lowest."""
        query = select(JobMatch).join(Job).where(JobMatch.user_id == user.id)

        if min_score is not None:
            query = query.where(JobMatch.overall_match_score >= min_score)

        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        matches = db.scalars(
            query.order_by(JobMatch.overall_match_score.desc()).offset(skip).limit(limit)
        ).all()

        return MatchListResponse(
            items=[self._to_match_response(m) for m in matches],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_match_detail(self, db: Session, user: User, job_id: uuid.UUID) -> JobMatchResponse:
        """Retrieves match details for a specific job."""
        match = db.scalar(
            select(JobMatch).where(JobMatch.job_id == job_id, JobMatch.user_id == user.id)
        )
        if match:
            return self._to_match_response(match)

        # Compute on the fly if job exists
        return self.match_job_for_user(db=db, user=user, job_id=job_id)


matching_service = MatchingService()
