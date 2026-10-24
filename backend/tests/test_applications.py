import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.security import hash_password
from app.models.application import Application
from app.models.job import Job
from app.models.match import JobMatch
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services.application.application_service import application_service


def _create_test_user_and_job(db: Session, email_prefix: str = "app_user"):
    user = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Application Tester",
    )
    db.add(user)
    db.flush()

    job = Job(
        user_id=user.id,
        company_name="Acme Corp",
        title="Senior Python Backend Engineer",
        normalized_title="senior python backend engineer",
        location="San Francisco, CA",
        work_mode="HYBRID",
        employment_type="FULL_TIME",
        salary_currency="USD",
        salary_min=140000.0,
        salary_max=180000.0,
        job_url="https://acme.com/jobs/123",
        platform_source="LINKEDIN",
        is_duplicate=False,
    )
    db.add(job)
    db.commit()
    return user, job


def test_track_application_default_applied(db_session: Session):
    """Tracking an application with default status APPLIED auto-assigns applied_date."""
    user, job = _create_test_user_and_job(db_session, "default_applied")

    app_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.APPLIED),
    )

    assert app_res.status == ApplicationStatus.APPLIED
    assert app_res.job_id == job.id
    assert app_res.user_id == user.id
    assert app_res.applied_date is not None
    assert app_res.job is not None
    assert app_res.job.company_name == "Acme Corp"


def test_track_application_discovered_status(db_session: Session):
    """Tracking an application with DISCOVERED status keeps applied_date as None."""
    user, job = _create_test_user_and_job(db_session, "discovered")

    app_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(
            job_id=job.id,
            status=ApplicationStatus.DISCOVERED,
            notes="Found via newsletter",
        ),
    )

    assert app_res.status == ApplicationStatus.DISCOVERED
    assert app_res.applied_date is None
    assert app_res.notes == "Found via newsletter"


def test_application_idempotent_tracking(db_session: Session):
    """Tracking an existing application updates status and notes instead of duplicating."""
    user, job = _create_test_user_and_job(db_session, "idempotent")

    first_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(
            job_id=job.id, status=ApplicationStatus.DISCOVERED, notes="First check"
        ),
    )

    second_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(
            job_id=job.id, status=ApplicationStatus.APPLIED, notes="Submitted application"
        ),
    )

    assert first_res.id == second_res.id
    assert second_res.status == ApplicationStatus.APPLIED
    assert second_res.applied_date is not None
    assert second_res.notes == "Submitted application"

    # Verify only 1 application row exists in DB
    all_apps = db_session.scalars(
        select(Application).where(Application.user_id == user.id)
    ).all()
    assert len(all_apps) == 1


def test_application_status_transition_lifecycle(db_session: Session):
    """Tests progression through pipeline stages: DISCOVERED -> APPLIED -> INTERVIEWING -> OFFER."""
    user, job = _create_test_user_and_job(db_session, "lifecycle")

    # 1. Start at DISCOVERED
    app_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.DISCOVERED),
    )
    assert app_res.status == ApplicationStatus.DISCOVERED
    assert app_res.applied_date is None

    # 2. Transition to APPLIED -> auto-sets applied_date
    app_res = application_service.update_application(
        db=db_session,
        user=user,
        application_id=app_res.id,
        data=ApplicationUpdate(status=ApplicationStatus.APPLIED),
    )
    assert app_res.status == ApplicationStatus.APPLIED
    assert app_res.applied_date is not None
    recorded_date = app_res.applied_date

    # 3. Transition to INTERVIEWING
    app_res = application_service.update_application(
        db=db_session,
        user=user,
        application_id=app_res.id,
        data=ApplicationUpdate(
            status=ApplicationStatus.INTERVIEWING,
            notes="Round 1 Technical Screening scheduled",
        ),
    )
    assert app_res.status == ApplicationStatus.INTERVIEWING
    assert app_res.applied_date == recorded_date  # Preserves initial applied_date
    assert "Screening scheduled" in app_res.notes

    # 4. Transition to OFFER
    app_res = application_service.update_application(
        db=db_session,
        user=user,
        application_id=app_res.id,
        data=ApplicationUpdate(status=ApplicationStatus.OFFER, notes="Offer received!"),
    )
    assert app_res.status == ApplicationStatus.OFFER


def test_list_applications_and_filtering(db_session: Session):
    """Tests application filtering by single status, multi-status, search term, and pagination."""
    user, job1 = _create_test_user_and_job(db_session, "filter_user")

    # Add second and third jobs for same user
    job2 = Job(
        user_id=user.id,
        company_name="Google",
        title="Software Engineer III",
        normalized_title="software engineer iii",
        work_mode="ON_SITE",
        is_duplicate=False,
    )
    job3 = Job(
        user_id=user.id,
        company_name="Stripe",
        title="Payments Infrastructure Lead",
        normalized_title="payments infrastructure lead",
        work_mode="REMOTE",
        is_duplicate=False,
    )
    db_session.add_all([job2, job3])
    db_session.commit()

    # Track applications
    application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job1.id, status=ApplicationStatus.APPLIED),
    )
    application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job2.id, status=ApplicationStatus.INTERVIEWING),
    )
    application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job3.id, status=ApplicationStatus.REJECTED),
    )

    # 1. List all
    all_res = application_service.list_applications(db=db_session, user=user)
    assert all_res.total == 3
    assert len(all_res.items) == 3

    # 2. Filter by single status
    applied_res = application_service.list_applications(
        db=db_session, user=user, status="APPLIED"
    )
    assert applied_res.total == 1
    assert applied_res.items[0].status == ApplicationStatus.APPLIED

    # 3. Filter by multiple comma-separated statuses
    multi_res = application_service.list_applications(
        db=db_session, user=user, status="APPLIED,INTERVIEWING"
    )
    assert multi_res.total == 2

    # 4. Search by company name
    stripe_res = application_service.list_applications(
        db=db_session, user=user, search="Stripe"
    )
    assert stripe_res.total == 1
    assert stripe_res.items[0].job.company_name == "Stripe"

    # 5. Search by job title
    eng_res = application_service.list_applications(
        db=db_session, user=user, search="Engineer"
    )
    assert eng_res.total == 2  # Acme Corp (Python Backend Engineer) + Google (Software Engineer III)


def test_pipeline_summary_metrics(db_session: Session):
    """Tests Kanban pipeline stage aggregation, active counts, and conversion percentages."""
    user, job1 = _create_test_user_and_job(db_session, "metrics_user")

    j2 = Job(user_id=user.id, company_name="Co2", title="Dev2", normalized_title="dev2", is_duplicate=False)
    j3 = Job(user_id=user.id, company_name="Co3", title="Dev3", normalized_title="dev3", is_duplicate=False)
    j4 = Job(user_id=user.id, company_name="Co4", title="Dev4", normalized_title="dev4", is_duplicate=False)
    db_session.add_all([j2, j3, j4])
    db_session.commit()

    application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=job1.id, status=ApplicationStatus.APPLIED)
    )
    application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=j2.id, status=ApplicationStatus.INTERVIEWING)
    )
    application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=j3.id, status=ApplicationStatus.OFFER)
    )
    application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=j4.id, status=ApplicationStatus.REJECTED)
    )

    summary = application_service.get_pipeline_summary(db=db_session, user=user)
    assert summary.total_applications == 4
    assert summary.stage_counts["APPLIED"] == 1
    assert summary.stage_counts["INTERVIEWING"] == 1
    assert summary.stage_counts["OFFER"] == 1
    assert summary.stage_counts["REJECTED"] == 1
    assert summary.stage_counts["DISCOVERED"] == 0
    assert summary.stage_counts["WITHDRAWN"] == 0

    # Active = APPLIED (1) + INTERVIEWING (1) + OFFER (1) = 3
    assert summary.active_count == 3

    # Interview rate: (INTERVIEWING + OFFER) / 4 = 2 / 4 = 50.0%
    assert summary.interview_rate_percentage == 50.0

    # Offer rate: OFFER / 4 = 1 / 4 = 25.0%
    assert summary.offer_rate_percentage == 25.0


def test_delete_application(db_session: Session):
    """Deleting an application untracks it and subsequent queries raise NotFoundError."""
    user, job = _create_test_user_and_job(db_session, "del_user")

    app_res = application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.APPLIED)
    )
    app_id = app_res.id

    application_service.delete_application(db=db_session, user=user, application_id=app_id)

    with pytest.raises(NotFoundError):
        application_service.get_application(db=db_session, user=user, application_id=app_id)


def test_auto_status_sync_from_email_event(db_session: Session):
    """Automatically promotes application stage on interview or offer email events."""
    user, job = _create_test_user_and_job(db_session, "auto_sync")

    # Initial state: APPLIED to Acme Corp
    application_service.create_or_update_application(
        db=db_session, user=user, data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.APPLIED)
    )

    # Email event arrives: Interview invitation
    promoted_interview = application_service.sync_status_from_email_event(
        db=db_session,
        user=user,
        company_name="Acme Corp",
        event_category="INTERVIEW_INVITATION",
    )
    assert promoted_interview is not None
    assert promoted_interview.status == ApplicationStatus.INTERVIEWING
    assert "Auto-updated" in promoted_interview.notes

    # Next email event arrives: Job Offer
    promoted_offer = application_service.sync_status_from_email_event(
        db=db_session,
        user=user,
        company_name="Acme Corp",
        event_category="JOB_OFFER",
    )
    assert promoted_offer is not None
    assert promoted_offer.status == ApplicationStatus.OFFER


def test_application_multi_tenant_isolation(db_session: Session):
    """User B cannot access or modify User A's applications."""
    user_a, job_a = _create_test_user_and_job(db_session, "tenant_a")
    user_b, job_b = _create_test_user_and_job(db_session, "tenant_b")

    app_a = application_service.create_or_update_application(
        db=db_session, user=user_a, data=ApplicationCreate(job_id=job_a.id, status=ApplicationStatus.APPLIED)
    )

    # 1. User B cannot get User A's application
    with pytest.raises(NotFoundError):
        application_service.get_application(db=db_session, user=user_b, application_id=app_a.id)

    # 2. User B cannot update User A's application
    with pytest.raises(NotFoundError):
        application_service.update_application(
            db=db_session,
            user=user_b,
            application_id=app_a.id,
            data=ApplicationUpdate(status=ApplicationStatus.REJECTED),
        )

    # 3. User B cannot delete User A's application
    with pytest.raises(NotFoundError):
        application_service.delete_application(
            db=db_session, user=user_b, application_id=app_a.id
        )

    # 4. User B cannot create an application targeting User A's job
    with pytest.raises(NotFoundError):
        application_service.create_or_update_application(
            db=db_session, user=user_b, data=ApplicationCreate(job_id=job_a.id)
        )


def test_api_application_routes(client: TestClient, db_session: Session):
    """Comprehensive test of full REST API workflow for applications."""
    # 1. Register & authenticate user
    email = f"api_app_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.scalar(select(User).where(User.email == email))

    # 2. Create a Job and Resume with Match Score
    job = Job(
        user_id=user.id,
        company_name="Vercel",
        title="Senior Frontend Engineer",
        normalized_title="senior frontend engineer",
        location="Remote",
        work_mode="REMOTE",
        is_duplicate=False,
    )
    resume = Resume(
        user_id=user.id,
        file_name="res.pdf",
        file_path="/res.pdf",
        extracted_text="Frontend Engineer Next.js React",
    )
    db_session.add_all([job, resume])
    db_session.flush()

    match = JobMatch(
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        overall_match_score=92.5,
        skill_score=95.0,
        experience_score=90.0,
        semantic_score=92.0,
        matched_skills=["React", "Next.js"],
        missing_required_skills=[],
        missing_preferred_skills=[],
        explanation_summary="Strong frontend match",
    )
    db_session.add(match)
    db_session.commit()

    # 3. POST /api/v1/applications -> Track application
    post_resp = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "job_id": str(job.id),
            "status": "APPLIED",
            "notes": "Applied via referral link",
        },
    )
    assert post_resp.status_code == 201
    app_data = post_resp.json()
    assert app_data["status"] == "APPLIED"
    assert app_data["job"]["company_name"] == "Vercel"
    assert app_data["match_score"] == 92.5
    app_id = app_data["id"]

    # 4. GET /api/v1/applications/{id} -> Get application
    get_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == app_id

    # 5. PATCH /api/v1/applications/{id} -> Move to INTERVIEWING
    patch_resp = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "INTERVIEWING", "notes": "Hiring manager call scheduled"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "INTERVIEWING"
    assert patch_resp.json()["notes"] == "Hiring manager call scheduled"

    # 6. GET /api/v1/applications -> List with filter
    list_resp = client.get("/api/v1/applications?status=INTERVIEWING", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 7. GET /api/v1/applications/pipeline/summary
    summary_resp = client.get("/api/v1/applications/pipeline/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_applications"] == 1
    assert summary_data["stage_counts"]["INTERVIEWING"] == 1
    assert summary_data["active_count"] == 1

    # 8. DELETE /api/v1/applications/{id}
    del_resp = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirm deletion
    get_after_del = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_track_application_not_applied_status(db_session: Session):
    """Tracking an application with NOT_APPLIED status succeeds and clears applied_date."""
    user, job = _create_test_user_and_job(db_session, "not_applied_test")

    # 1. Track initially as APPLIED (Like)
    app_res = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.APPLIED),
    )
    assert app_res.status == ApplicationStatus.APPLIED
    assert app_res.applied_date is not None

    # 2. Switch to NOT_APPLIED (Dislike)
    app_res_dislike = application_service.create_or_update_application(
        db=db_session,
        user=user,
        data=ApplicationCreate(job_id=job.id, status=ApplicationStatus.NOT_APPLIED),
    )
    assert app_res_dislike.status == ApplicationStatus.NOT_APPLIED
    assert app_res_dislike.applied_date is None

    # 3. Verify in list_applications
    list_res = application_service.list_applications(
        db=db_session, user=user, status="NOT_APPLIED"
    )
    assert list_res.total == 1
    assert list_res.items[0].status == ApplicationStatus.NOT_APPLIED

    # 4. Verify in pipeline summary
    summary = application_service.get_pipeline_summary(db=db_session, user=user)
    assert summary.stage_counts["NOT_APPLIED"] == 1

