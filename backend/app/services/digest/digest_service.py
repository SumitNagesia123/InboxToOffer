import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.application import Application
from app.models.audit import DailyDigest
from app.models.email import Email
from app.models.job import Job
from app.models.match import JobMatch
from app.models.preference import UserPreference
from app.models.user import User
from app.schemas.digest import (
    DailyDigestListResponse,
    DailyDigestResponse,
    DigestJobItem,
    DigestPreviewResponse,
    TriggerDigestResponse,
    UserPreferenceResponse,
    UserPreferenceUpdate,
)
from app.services.digest.digest_generator import digest_generator
from app.services.digest.email_dispatcher import email_dispatcher
from app.services.notification.notification_service import notification_service


class DigestService:
    """Orchestrates job digest compilation, personalized filtering, dispatch, and history."""

    def get_or_create_user_preferences(self, db: Session, user: User) -> UserPreference:
        """Retrieves or initializes user preferences with sensible defaults."""
        pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
        if not pref:
            pref = UserPreference(
                user_id=user.id,
                digest_enabled=True,
                digest_time="22:00",
                preferred_work_modes=[],
                min_desired_salary=None,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
            logger.info("Initialized default preferences for user %s", str(user.id))
        return pref

    def update_user_preferences(
        self, db: Session, user: User, data: UserPreferenceUpdate
    ) -> UserPreferenceResponse:
        """Updates user digest and job hunt filter preferences."""
        pref = self.get_or_create_user_preferences(db=db, user=user)

        if data.digest_enabled is not None:
            pref.digest_enabled = data.digest_enabled
        if data.digest_time is not None:
            pref.digest_time = data.digest_time
        if data.preferred_work_modes is not None:
            pref.preferred_work_modes = data.preferred_work_modes
        if data.min_desired_salary is not None:
            pref.min_desired_salary = data.min_desired_salary

        db.commit()
        db.refresh(pref)
        logger.info("Updated preferences for user %s", str(user.id))
        return UserPreferenceResponse.model_validate(pref)

    def _format_salary(
        self, currency: Optional[str], min_sal: Optional[float], max_sal: Optional[float]
    ) -> Optional[str]:
        """Formats salary into human-readable range."""
        if not min_sal and not max_sal:
            return None
        curr = currency or "$"
        if min_sal and max_sal:
            if min_sal >= 1000 and max_sal >= 1000:
                return f"{curr}{int(min_sal / 1000)}k - {curr}{int(max_sal / 1000)}k"
            return f"{curr}{int(min_sal):,} - {curr}{int(max_sal):,}"
        val = min_sal or max_sal
        if val >= 1000:
            return f"{curr}{int(val / 1000)}k"
        return f"{curr}{int(val):,}"

    def generate_digest_content(self, db: Session, user: User) -> DigestPreviewResponse:
        """Compiles matching jobs, interview updates, and renders HTML/text email content."""
        pref = self.get_or_create_user_preferences(db=db, user=user)
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%A, %B %d, %Y")

        # 1. Query non-duplicate jobs for user
        job_stmt = select(Job).where(Job.user_id == user.id, Job.is_duplicate.is_(False))

        # Filter by preferred work modes if specified
        if pref.preferred_work_modes:
            job_stmt = job_stmt.where(Job.work_mode.in_(pref.preferred_work_modes))

        # Filter by min desired salary if specified
        if pref.min_desired_salary:
            job_stmt = job_stmt.where(
                (Job.salary_max >= pref.min_desired_salary)
                | (Job.salary_min >= pref.min_desired_salary)
                | (Job.salary_min.is_(None))
            )

        jobs = db.scalars(job_stmt).all()
        total_jobs_evaluated = len(jobs)

        # 2. Gather matches from job_matches
        job_ids = [j.id for j in jobs]
        matches_map: Dict[uuid.UUID, JobMatch] = {}
        if job_ids:
            matches = db.scalars(
                select(JobMatch).where(
                    JobMatch.user_id == user.id,
                    JobMatch.job_id.in_(job_ids),
                )
            ).all()
            for m in matches:
                matches_map[m.job_id] = m

        # 3. Build ranked DigestJobItems
        digest_items: List[DigestJobItem] = []
        for job in jobs:
            match = matches_map.get(job.id)
            score = match.overall_match_score if match else 50.0
            matched_skills = match.matched_skills if match else []

            # Only include reasonable matches (score >= 50.0)
            if score >= 50.0:
                digest_items.append(
                    DigestJobItem(
                        job_id=job.id,
                        company_name=job.company_name,
                        title=job.title,
                        location=job.location,
                        work_mode=job.work_mode,
                        salary_formatted=self._format_salary(
                            job.salary_currency, job.salary_min, job.salary_max
                        ),
                        match_score=score,
                        matched_skills=matched_skills,
                        job_url=job.job_url,
                    )
                )

        # Sort top matches by score descending, limit to top 10
        digest_items.sort(key=lambda x: x.match_score, reverse=True)
        top_matches = digest_items[:10]

        # 4. Check active interview updates
        interview_count = db.scalar(
            select(func.count(Application.id)).where(
                Application.user_id == user.id,
                Application.status == "INTERVIEWING",
            )
        ) or 0

        # 5. Render HTML and text
        recipient_name = user.full_name or user.email.split("@")[0]
        html_content = digest_generator.render_digest_html(
            recipient_name=recipient_name,
            date_str=date_str,
            total_jobs_evaluated=total_jobs_evaluated,
            top_matches=top_matches,
            interview_count=interview_count,
        )
        text_content = digest_generator.render_digest_text(
            recipient_name=recipient_name,
            date_str=date_str,
            total_jobs_evaluated=total_jobs_evaluated,
            top_matches=top_matches,
            interview_count=interview_count,
        )

        subject = f"AI Job Intelligence: {len(top_matches)} Top Matches for {date_str}"

        return DigestPreviewResponse(
            recipient_email=user.email,
            subject=subject,
            date_formatted=date_str,
            total_jobs_evaluated=total_jobs_evaluated,
            top_matches_count=len(top_matches),
            top_matches=top_matches,
            interview_alerts_count=interview_count,
            html_content=html_content,
            text_content=text_content,
        )

    def dispatch_digest_for_user(
        self, db: Session, user: User, force: bool = False
    ) -> TriggerDigestResponse:
        """Generates, sends, and audits daily job digest for target user."""
        pref = self.get_or_create_user_preferences(db=db, user=user)

        if not pref.digest_enabled and not force:
            return TriggerDigestResponse(
                success=False,
                message="Daily digest is disabled in user preferences.",
                digest_id=None,
                recipient_email=user.email,
                top_matches_count=0,
                delivery_status="DISABLED",
            )

        preview = self.generate_digest_content(db=db, user=user)

        # Count total emails processed
        total_emails = db.scalar(
            select(func.count(Email.id)).where(Email.user_id == user.id)
        ) or 0

        # Dispatch email
        success, delivery_status = email_dispatcher.send_email(
            recipient_email=user.email,
            subject=preview.subject,
            html_content=preview.html_content,
            text_content=preview.text_content,
        )

        # Audit record
        digest_record = DailyDigest(
            user_id=user.id,
            sent_at=datetime.now(timezone.utc),
            total_emails_processed=total_emails,
            new_jobs_count=preview.total_jobs_evaluated,
            top_matches_count=preview.top_matches_count,
            recipient_email=user.email,
            status="SENT" if success else "FAILED",
        )
        db.add(digest_record)

        # In-app notification
        notification_service.create_notification(
            db=db,
            user_id=user.id,
            title="Daily Job Digest Dispatched",
            message=f"Sent daily digest with {preview.top_matches_count} matching positions to {user.email}.",
            category="DIGEST",
        )

        db.commit()
        db.refresh(digest_record)
        logger.info("Dispatched digest %s to user %s (%s)", str(digest_record.id), str(user.id), delivery_status)

        return TriggerDigestResponse(
            success=success,
            message="Daily digest dispatched successfully.",
            digest_id=digest_record.id,
            recipient_email=user.email,
            top_matches_count=preview.top_matches_count,
            delivery_status=delivery_status,
        )

    def dispatch_scheduled_daily_digests(self, db: Session) -> Dict[str, int]:
        """Batch dispatcher for all users who have daily digest enabled."""
        users = db.scalars(
            select(User)
            .join(UserPreference, User.id == UserPreference.user_id)
            .where(UserPreference.digest_enabled.is_(True))
        ).all()

        success_count = 0
        fail_count = 0
        for user in users:
            try:
                res = self.dispatch_digest_for_user(db=db, user=user)
                if res.success:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error("Failed scheduled digest for user %s: %s", str(user.id), str(e))
                fail_count += 1

        return {"dispatched": success_count, "failed": fail_count}

    def list_digest_history(
        self, db: Session, user: User, skip: int = 0, limit: int = 20
    ) -> DailyDigestListResponse:
        """Retrieves history of dispatched digests for the user."""
        stmt = (
            select(DailyDigest)
            .where(DailyDigest.user_id == user.id)
            .order_by(DailyDigest.sent_at.desc())
        )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = db.scalars(stmt.offset(skip).limit(limit)).all()

        return DailyDigestListResponse(
            items=[DailyDigestResponse.model_validate(d) for d in items],
            total=total,
            skip=skip,
            limit=limit,
        )


digest_service = DigestService()
