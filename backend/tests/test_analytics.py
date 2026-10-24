import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.application import Application
from app.models.audit import DailyDigest, Notification
from app.models.email import Email
from app.models.job import Job, JobSkill
from app.models.match import JobMatch
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.models.user import User
from app.services.analytics.analytics_service import analytics_service


def _get_or_create_skill(db: Session, name: str, normalized_name: str, category: str = "Technical") -> Skill:
    existing = db.scalar(select(Skill).where(Skill.normalized_name == normalized_name))
    if existing:
        return existing
    skill = Skill(name=name, normalized_name=normalized_name, category=category)
    db.add(skill)
    db.flush()
    return skill


def _create_user(db: Session, email_prefix: str = "analytics_user") -> User:
    user = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Analytics Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_dashboard_kpis_empty_state(db_session: Session):
    """When user has no data, KPIs return zeroes with no division by zero errors."""
    user = _create_user(db_session, "empty_kpi")

    kpis = analytics_service.get_dashboard_kpis(db=db_session, user=user)
    assert kpis.total_emails_ingested == 0
    assert kpis.total_jobs_discovered == 0
    assert kpis.unique_jobs_count == 0
    assert kpis.duplicate_jobs_count == 0
    assert kpis.duplicate_rate_percentage == 0.0
    assert kpis.high_match_jobs_count == 0
    assert kpis.average_match_score == 0.0
    assert kpis.total_applications == 0
    assert kpis.active_applications == 0
    assert kpis.interview_rate_percentage == 0.0
    assert kpis.offer_rate_percentage == 0.0


def test_dashboard_kpis_calculation(db_session: Session):
    """Verifies all KPI mathematical computations across emails, jobs, matches, and applications."""
    user = _create_user(db_session, "calc_user")

    # 1. Ingested Emails
    e1 = Email(
        user_id=user.id,
        gmail_message_id="msg_1",
        sender="jobs@linkedin.com",
        recipient=user.email,
        subject="3 New Job Opportunities",
        body_text="Job openings",
        received_at=datetime.now(timezone.utc),
    )
    e2 = Email(
        user_id=user.id,
        gmail_message_id="msg_2",
        sender="careers@indeed.com",
        recipient=user.email,
        subject="Indeed Application Update",
        body_text="Update on application",
        received_at=datetime.now(timezone.utc),
    )
    db_session.add_all([e1, e2])

    # 2. Jobs (3 total: 2 unique, 1 duplicate)
    j1 = Job(
        user_id=user.id,
        company_name="Alpha Tech",
        title="Backend Engineer",
        normalized_title="backend engineer",
        work_mode="REMOTE",
        platform_source="LINKEDIN",
        is_duplicate=False,
    )
    j2 = Job(
        user_id=user.id,
        company_name="Beta Systems",
        title="Full Stack Engineer",
        normalized_title="full stack engineer",
        work_mode="HYBRID",
        platform_source="INDEED",
        is_duplicate=False,
    )
    j3 = Job(
        user_id=user.id,
        company_name="Alpha Tech",
        title="Backend Engineer",
        normalized_title="backend engineer",
        work_mode="REMOTE",
        platform_source="GLASSDOOR",
        is_duplicate=True,
    )
    db_session.add_all([j1, j2, j3])
    db_session.flush()

    # 3. Matches
    resume = Resume(
        user_id=user.id,
        file_name="resume.pdf",
        file_path="/res.pdf",
        extracted_text="Python Engineer",
    )
    db_session.add(resume)
    db_session.flush()

    m1 = JobMatch(
        user_id=user.id,
        job_id=j1.id,
        resume_id=resume.id,
        overall_match_score=85.0,
        skill_score=85.0,
        experience_score=85.0,
        semantic_score=85.0,
        explanation_summary="Good match",
    )
    m2 = JobMatch(
        user_id=user.id,
        job_id=j2.id,
        resume_id=resume.id,
        overall_match_score=65.0,
        skill_score=65.0,
        experience_score=65.0,
        semantic_score=65.0,
        explanation_summary="Moderate match",
    )
    db_session.add_all([m1, m2])

    # 4. Applications (1 APPLIED, 1 INTERVIEWING)
    app1 = Application(user_id=user.id, job_id=j1.id, status="APPLIED")
    app2 = Application(user_id=user.id, job_id=j2.id, status="INTERVIEWING")
    db_session.add_all([app1, app2])
    db_session.commit()

    # Execute KPI calculation
    kpis = analytics_service.get_dashboard_kpis(db=db_session, user=user)

    assert kpis.total_emails_ingested == 2
    assert kpis.total_jobs_discovered == 3
    assert kpis.unique_jobs_count == 2
    assert kpis.duplicate_jobs_count == 1
    assert kpis.duplicate_rate_percentage == 33.3  # (1/3)*100
    assert kpis.high_match_jobs_count == 1  # only m1 (85.0) >= 70.0
    assert kpis.average_match_score == 75.0  # (85 + 65) / 2
    assert kpis.total_applications == 2
    assert kpis.active_applications == 2  # APPLIED + INTERVIEWING
    assert kpis.interview_rate_percentage == 50.0  # 1 out of 2 is INTERVIEWING
    assert kpis.offer_rate_percentage == 0.0


def test_pipeline_and_work_mode_distributions(db_session: Session):
    """Verifies pipeline stage breakdown and work mode distributions."""
    user = _create_user(db_session, "dist_user")

    # Add 2 jobs: 1 REMOTE, 1 HYBRID
    j1 = Job(user_id=user.id, company_name="Co1", title="Role1", normalized_title="r1", work_mode="REMOTE", is_duplicate=False)
    j2 = Job(user_id=user.id, company_name="Co2", title="Role2", normalized_title="r2", work_mode="HYBRID", is_duplicate=False)
    db_session.add_all([j1, j2])
    db_session.flush()

    # Add applications: 1 APPLIED, 1 OFFER
    app1 = Application(user_id=user.id, job_id=j1.id, status="APPLIED")
    app2 = Application(user_id=user.id, job_id=j2.id, status="OFFER")
    db_session.add_all([app1, app2])
    db_session.commit()

    analytics = analytics_service.get_dashboard_analytics(db=db_session, user=user)

    # Pipeline distribution
    stage_map = {d.status: d for d in analytics.pipeline_distribution}
    assert stage_map["APPLIED"].count == 1
    assert stage_map["APPLIED"].percentage == 50.0
    assert stage_map["OFFER"].count == 1
    assert stage_map["OFFER"].percentage == 50.0
    assert stage_map["DISCOVERED"].count == 0

    # Work mode distribution
    wm_map = {w.work_mode: w for w in analytics.work_mode_distribution}
    assert wm_map["REMOTE"].count == 1
    assert wm_map["REMOTE"].percentage == 50.0
    assert wm_map["HYBRID"].count == 1
    assert wm_map["HYBRID"].percentage == 50.0


def test_in_demand_skills_and_candidate_possession(db_session: Session):
    """Tests identifying market skill demand and cross-referencing candidate resume possession."""
    user = _create_user(db_session, "skills_user")

    # Skills master
    py_skill = _get_or_create_skill(db_session, "Python", "python", "Programming Language")
    k8s_skill = _get_or_create_skill(db_session, "Kubernetes", "kubernetes", "DevOps")

    # Candidate active resume with Python only
    resume = Resume(
        user_id=user.id,
        file_name="res.pdf",
        file_path="/res.pdf",
        extracted_text="Python Dev",
    )
    db_session.add(resume)
    db_session.flush()

    db_session.add(ResumeSkill(resume_id=resume.id, skill_id=py_skill.id, years_experience=4.0))

    # Job requiring Python and Kubernetes
    job = Job(
        user_id=user.id,
        company_name="ScaleUp",
        title="Infrastructure Engineer",
        normalized_title="infrastructure engineer",
        is_duplicate=False,
    )
    db_session.add(job)
    db_session.flush()

    db_session.add(JobSkill(job_id=job.id, skill_id=py_skill.id, is_required=True))
    db_session.add(JobSkill(job_id=job.id, skill_id=k8s_skill.id, is_required=True))
    db_session.commit()

    analytics = analytics_service.get_dashboard_analytics(db=db_session, user=user)

    skill_map = {s.name: s for s in analytics.top_in_demand_skills}
    assert "Python" in skill_map
    assert skill_map["Python"].candidate_has_skill is True
    assert "Kubernetes" in skill_map
    assert skill_map["Kubernetes"].candidate_has_skill is False


def test_match_score_histogram_buckets(db_session: Session):
    """Verifies grouping of match scores into distribution buckets."""
    user = _create_user(db_session, "bucket_user")

    job = Job(user_id=user.id, company_name="C1", title="T1", normalized_title="t1", is_duplicate=False)
    resume = Resume(user_id=user.id, file_name="r.txt", file_path="/r.txt", extracted_text="test")
    db_session.add_all([job, resume])
    db_session.flush()

    # Scores: 95.0 (90-100%), 82.0 (80-89%), 55.0 (<60%)
    m1 = JobMatch(user_id=user.id, job_id=job.id, resume_id=resume.id, overall_match_score=95.0, skill_score=95.0, experience_score=95.0, semantic_score=95.0, explanation_summary="s")
    db_session.add(m1)
    db_session.commit()

    analytics = analytics_service.get_dashboard_analytics(db=db_session, user=user)
    buckets = {b.range_label: b for b in analytics.match_score_distribution}

    assert buckets["90% - 100%"].count == 1
    assert buckets["90% - 100%"].percentage == 100.0
    assert buckets["80% - 89%"].count == 0


def test_activity_timeline_synthesis(db_session: Session):
    """Verifies activity timeline combines applications, jobs, digests, and notifications."""
    user = _create_user(db_session, "timeline_user")

    # Add notification
    n = Notification(user_id=user.id, title="Test Notification", message="Alert", category="SYSTEM")
    # Add digest
    d = DailyDigest(user_id=user.id, recipient_email=user.email, top_matches_count=3, status="SENT")
    db_session.add_all([n, d])
    db_session.commit()

    analytics = analytics_service.get_dashboard_analytics(db=db_session, user=user)
    assert len(analytics.recent_activities) >= 2
    types = [a.activity_type for a in analytics.recent_activities]
    assert "NOTIFICATION" in types
    assert "DIGEST" in types


def test_skills_gap_analysis(db_session: Session):
    """Verifies skills gap calculations and candidate market coverage percentage."""
    user = _create_user(db_session, "gap_user")

    py_skill = _get_or_create_skill(db_session, "Python", "python", "Programming")
    go_skill = _get_or_create_skill(db_session, "Go", "go", "Programming")

    resume = Resume(user_id=user.id, file_name="r.pdf", file_path="/r.pdf", extracted_text="Python")
    db_session.add(resume)
    db_session.flush()

    db_session.add(ResumeSkill(resume_id=resume.id, skill_id=py_skill.id, years_experience=3.0))

    # Job requiring Python and Go
    job = Job(user_id=user.id, company_name="GoTech", title="Dev", normalized_title="dev", is_duplicate=False)
    db_session.add(job)
    db_session.flush()

    db_session.add(JobSkill(job_id=job.id, skill_id=py_skill.id, is_required=True))
    db_session.add(JobSkill(job_id=job.id, skill_id=go_skill.id, is_required=True))
    db_session.commit()

    gap_res = analytics_service.get_skills_gap_analytics(db=db_session, user=user)
    assert gap_res.market_unique_skills == 2
    assert gap_res.matching_skills_count == 1
    assert gap_res.missing_skills_count == 1
    assert gap_res.coverage_percentage == 50.0


def test_analytics_multi_tenant_isolation(db_session: Session):
    """User B's analytics strictly isolate User A's data."""
    user_a = _create_user(db_session, "tenant_a")
    user_b = _create_user(db_session, "tenant_b")

    # Add 5 jobs for User A
    for i in range(5):
        db_session.add(
            Job(
                user_id=user_a.id,
                company_name=f"Company {i}",
                title=f"Engineer {i}",
                normalized_title=f"engineer {i}",
                is_duplicate=False,
            )
        )
    db_session.commit()

    # User B should see 0 jobs in KPIs
    b_kpis = analytics_service.get_dashboard_kpis(db=db_session, user=user_b)
    assert b_kpis.total_jobs_discovered == 0
    assert b_kpis.unique_jobs_count == 0

    # User A should see 5 jobs
    a_kpis = analytics_service.get_dashboard_kpis(db=db_session, user=user_a)
    assert a_kpis.total_jobs_discovered == 5


def test_api_analytics_endpoints(client: TestClient, db_session: Session):
    """Full HTTP API test of analytics endpoints."""
    email = f"api_analytics_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/analytics/kpis
    kpi_resp = client.get("/api/v1/analytics/kpis", headers=headers)
    assert kpi_resp.status_code == 200
    kpi_data = kpi_resp.json()
    assert "total_emails_ingested" in kpi_data
    assert "duplicate_rate_percentage" in kpi_data

    # 2. GET /api/v1/analytics
    full_resp = client.get("/api/v1/analytics", headers=headers)
    assert full_resp.status_code == 200
    full_data = full_resp.json()
    assert "kpis" in full_data
    assert "pipeline_distribution" in full_data
    assert "work_mode_distribution" in full_data
    assert "top_in_demand_skills" in full_data
    assert "recent_activities" in full_data

    # 3. GET /api/v1/analytics/skills-gap
    gap_resp = client.get("/api/v1/analytics/skills-gap", headers=headers)
    assert gap_resp.status_code == 200
    gap_data = gap_resp.json()
    assert "candidate_total_skills" in gap_data
    assert "coverage_percentage" in gap_data
