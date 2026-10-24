import uuid
from typing import Dict, List, Optional, Set
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.audit import DailyDigest, Notification
from app.models.email import Email
from app.models.job import Job, JobSkill
from app.models.match import JobMatch
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.models.user import User
from app.schemas.analytics import (
    ActivityItem,
    DashboardAnalyticsResponse,
    DashboardOverviewKPIs,
    PlatformSourceDistribution,
    ScoreBucket,
    SkillsGapItem,
    SkillsGapResponse,
    StatusDistribution,
    TopInDemandSkill,
    WorkModeDistribution,
)


class AnalyticsService:
    """Aggregates multi-tenant performance metrics, pipeline funnel analytics, and market skill demands."""

    ALL_STATUSES = [
        "DISCOVERED",
        "APPLIED",
        "INTERVIEWING",
        "REJECTED",
        "OFFER",
        "WITHDRAWN",
    ]

    def get_dashboard_kpis(self, db: Session, user: User) -> DashboardOverviewKPIs:
        """Computes key performance indicators strictly isolated to the authenticated user."""
        # 1. Emails
        total_emails = db.scalar(
            select(func.count(Email.id)).where(Email.user_id == user.id)
        ) or 0

        # 2. Jobs & Duplicates
        total_jobs = db.scalar(
            select(func.count(Job.id)).where(Job.user_id == user.id)
        ) or 0

        duplicate_jobs = db.scalar(
            select(func.count(Job.id)).where(
                Job.user_id == user.id, Job.is_duplicate.is_(True)
            )
        ) or 0

        unique_jobs = total_jobs - duplicate_jobs
        dup_rate = round((duplicate_jobs / total_jobs) * 100.0, 1) if total_jobs > 0 else 0.0

        # 3. Matches
        high_matches = db.scalar(
            select(func.count(JobMatch.id)).where(
                JobMatch.user_id == user.id, JobMatch.overall_match_score >= 70.0
            )
        ) or 0

        avg_score = db.scalar(
            select(func.avg(JobMatch.overall_match_score)).where(
                JobMatch.user_id == user.id
            )
        )
        avg_score_val = round(float(avg_score), 1) if avg_score is not None else 0.0

        # 4. Applications Funnel
        app_counts = dict(
            db.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.user_id == user.id)
                .group_by(Application.status)
            ).all()
        )

        total_apps = sum(app_counts.values())
        active_apps = (
            app_counts.get("APPLIED", 0)
            + app_counts.get("INTERVIEWING", 0)
            + app_counts.get("OFFER", 0)
        )

        funnel_base = (
            app_counts.get("APPLIED", 0)
            + app_counts.get("INTERVIEWING", 0)
            + app_counts.get("OFFER", 0)
            + app_counts.get("REJECTED", 0)
        )

        interview_rate = 0.0
        offer_rate = 0.0
        if funnel_base > 0:
            interviewing_or_offer = app_counts.get("INTERVIEWING", 0) + app_counts.get("OFFER", 0)
            interview_rate = round((interviewing_or_offer / funnel_base) * 100.0, 1)
            offer_rate = round((app_counts.get("OFFER", 0) / funnel_base) * 100.0, 1)

        return DashboardOverviewKPIs(
            total_emails_ingested=total_emails,
            total_jobs_discovered=total_jobs,
            unique_jobs_count=unique_jobs,
            duplicate_jobs_count=duplicate_jobs,
            duplicate_rate_percentage=dup_rate,
            high_match_jobs_count=high_matches,
            average_match_score=avg_score_val,
            total_applications=total_apps,
            active_applications=active_apps,
            interview_rate_percentage=interview_rate,
            offer_rate_percentage=offer_rate,
        )

    def get_dashboard_analytics(self, db: Session, user: User) -> DashboardAnalyticsResponse:
        """Builds full comprehensive analytics dataset for Dashboard and Analytics pages."""
        # 1. KPIs
        kpis = self.get_dashboard_kpis(db=db, user=user)

        # 2. Pipeline Stage Distribution
        app_counts = dict(
            db.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.user_id == user.id)
                .group_by(Application.status)
            ).all()
        )
        total_apps = kpis.total_applications
        pipeline_dist: List[StatusDistribution] = []
        for st in self.ALL_STATUSES:
            cnt = app_counts.get(st, 0)
            pct = round((cnt / total_apps) * 100.0, 1) if total_apps > 0 else 0.0
            pipeline_dist.append(StatusDistribution(status=st, count=cnt, percentage=pct))

        # 3. Work Mode Distribution (non-duplicate jobs)
        wm_counts = db.execute(
            select(Job.work_mode, func.count(Job.id))
            .where(Job.user_id == user.id, Job.is_duplicate.is_(False))
            .group_by(Job.work_mode)
        ).all()
        unique_jobs = kpis.unique_jobs_count
        work_mode_dist = [
            WorkModeDistribution(
                work_mode=wm,
                count=cnt,
                percentage=round((cnt / unique_jobs) * 100.0, 1) if unique_jobs > 0 else 0.0,
            )
            for wm, cnt in wm_counts
        ]

        # 4. Platform Source Distribution (non-duplicate jobs)
        src_counts = db.execute(
            select(Job.platform_source, func.count(Job.id))
            .where(Job.user_id == user.id, Job.is_duplicate.is_(False))
            .group_by(Job.platform_source)
        ).all()
        platform_dist = [
            PlatformSourceDistribution(
                platform_source=src,
                count=cnt,
                percentage=round((cnt / unique_jobs) * 100.0, 1) if unique_jobs > 0 else 0.0,
            )
            for src, cnt in src_counts
        ]

        # 5. Candidate Skills Resolution
        candidate_skills: Set[str] = set()
        active_resume = db.scalar(
            select(Resume).where(Resume.user_id == user.id)
        )
        if active_resume:
            r_skills = db.execute(
                select(Skill.normalized_name)
                .join(ResumeSkill, Skill.id == ResumeSkill.skill_id)
                .where(ResumeSkill.resume_id == active_resume.id)
            ).all()
            candidate_skills = {s[0] for s in r_skills}

        # 6. Top In-Demand Skills in Market
        skill_counts = db.execute(
            select(Skill.name, Skill.category, Skill.normalized_name, func.count(JobSkill.job_id))
            .join(JobSkill, Skill.id == JobSkill.skill_id)
            .join(Job, JobSkill.job_id == Job.id)
            .where(Job.user_id == user.id, Job.is_duplicate.is_(False))
            .group_by(Skill.id, Skill.name, Skill.category, Skill.normalized_name)
            .order_by(func.count(JobSkill.job_id).desc())
            .limit(10)
        ).all()

        top_skills = [
            TopInDemandSkill(
                name=name,
                category=cat or "General",
                demand_count=cnt,
                candidate_has_skill=(norm in candidate_skills),
            )
            for name, cat, norm, cnt in skill_counts
        ]

        # 7. Match Score Distribution Buckets
        all_matches = db.scalars(
            select(JobMatch.overall_match_score).where(JobMatch.user_id == user.id)
        ).all()
        total_m = len(all_matches)

        buckets = [
            {"label": "90% - 100%", "count": sum(1 for s in all_matches if s >= 90.0)},
            {"label": "80% - 89%", "count": sum(1 for s in all_matches if 80.0 <= s < 90.0)},
            {"label": "70% - 79%", "count": sum(1 for s in all_matches if 70.0 <= s < 80.0)},
            {"label": "60% - 69%", "count": sum(1 for s in all_matches if 60.0 <= s < 70.0)},
            {"label": "< 60%", "count": sum(1 for s in all_matches if s < 60.0)},
        ]
        score_distribution = [
            ScoreBucket(
                range_label=b["label"],
                count=b["count"],
                percentage=round((b["count"] / total_m) * 100.0, 1) if total_m > 0 else 0.0,
            )
            for b in buckets
        ]

        # 8. Activity Timeline
        activities: List[ActivityItem] = []

        # Recent applications
        recent_apps = db.scalars(
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.user_id == user.id)
            .order_by(Application.updated_at.desc())
            .limit(5)
        ).all()
        for app in recent_apps:
            comp = app.job.company_name if app.job else "Company"
            title = app.job.title if app.job else "Role"
            activities.append(
                ActivityItem(
                    id=app.id,
                    activity_type="APPLICATION",
                    title=f"Application status: {app.status}",
                    description=f"{title} at {comp}",
                    timestamp=app.updated_at,
                )
            )

        # Recent jobs
        recent_jobs = db.scalars(
            select(Job)
            .where(Job.user_id == user.id, Job.is_duplicate.is_(False))
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        for job in recent_jobs:
            activities.append(
                ActivityItem(
                    id=job.id,
                    activity_type="JOB",
                    title="New job discovered",
                    description=f"{job.title} at {job.company_name} ({job.work_mode})",
                    timestamp=job.created_at,
                )
            )

        # Recent daily digests
        recent_digests = db.scalars(
            select(DailyDigest)
            .where(DailyDigest.user_id == user.id)
            .order_by(DailyDigest.sent_at.desc())
            .limit(3)
        ).all()
        for d in recent_digests:
            activities.append(
                ActivityItem(
                    id=d.id,
                    activity_type="DIGEST",
                    title="Daily Digest Dispatched",
                    description=f"{d.top_matches_count} matching positions delivered to {d.recipient_email}",
                    timestamp=d.sent_at,
                )
            )

        # Recent notifications
        recent_notifs = db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(5)
        ).all()
        for n in recent_notifs:
            activities.append(
                ActivityItem(
                    id=n.id,
                    activity_type="NOTIFICATION",
                    title=n.title,
                    description=n.message,
                    timestamp=n.created_at,
                )
            )

        # Sort combined activity timeline descending, take top 15
        activities.sort(key=lambda a: a.timestamp, reverse=True)
        recent_activities = activities[:15]

        return DashboardAnalyticsResponse(
            kpis=kpis,
            pipeline_distribution=pipeline_dist,
            work_mode_distribution=work_mode_dist,
            platform_distribution=platform_dist,
            top_in_demand_skills=top_skills,
            match_score_distribution=score_distribution,
            recent_activities=recent_activities,
        )

    def get_skills_gap_analytics(self, db: Session, user: User) -> SkillsGapResponse:
        """Evaluates market skill requirements against candidate resume skills."""
        # 1. Candidate skills
        candidate_skills_dict: Dict[str, float] = {}
        active_resume = db.scalar(
            select(Resume).where(Resume.user_id == user.id)
        )
        if active_resume:
            r_skills = db.execute(
                select(Skill.normalized_name, ResumeSkill.years_experience)
                .join(ResumeSkill, Skill.id == ResumeSkill.skill_id)
                .where(ResumeSkill.resume_id == active_resume.id)
            ).all()
            for norm, yrs in r_skills:
                candidate_skills_dict[norm] = yrs

        # 2. Market skill demand across user's jobs
        skills_demand = db.execute(
            select(Skill.name, Skill.category, Skill.normalized_name, func.count(JobSkill.job_id))
            .join(JobSkill, Skill.id == JobSkill.skill_id)
            .join(Job, JobSkill.job_id == Job.id)
            .where(Job.user_id == user.id, Job.is_duplicate.is_(False))
            .group_by(Skill.id, Skill.name, Skill.category, Skill.normalized_name)
            .order_by(func.count(JobSkill.job_id).desc())
            .limit(30)
        ).all()

        breakdown: List[SkillsGapItem] = []
        matching_count = 0
        missing_count = 0

        for name, cat, norm, count in skills_demand:
            has_skill = norm in candidate_skills_dict
            yrs = candidate_skills_dict.get(norm)
            if has_skill:
                matching_count += 1
            else:
                missing_count += 1

            breakdown.append(
                SkillsGapItem(
                    skill_name=name,
                    category=cat or "General",
                    job_mention_count=count,
                    is_possessed_by_candidate=has_skill,
                    candidate_years_experience=yrs,
                )
            )

        total_market = len(skills_demand)
        coverage = round((matching_count / total_market) * 100.0, 1) if total_market > 0 else 0.0

        return SkillsGapResponse(
            candidate_total_skills=len(candidate_skills_dict),
            market_unique_skills=total_market,
            matching_skills_count=matching_count,
            missing_skills_count=missing_count,
            coverage_percentage=coverage,
            skills_breakdown=breakdown,
        )


analytics_service = AnalyticsService()
