import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.security import hash_password
from app.models.audit import DailyDigest, Notification
from app.models.job import Job
from app.models.match import JobMatch
from app.models.preference import UserPreference
from app.models.resume import Resume
from app.models.user import User
from app.schemas.digest import UserPreferenceUpdate
from app.schemas.notification import NotificationCategory
from app.services.digest.digest_service import digest_service
from app.services.notification.notification_service import notification_service


def _create_user(db: Session, email_prefix: str = "digest_user") -> User:
    user = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Digest Tester",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_notification_creation_and_listing(db_session: Session):
    """Verifies in-app notification creation, descending sort, and is_read filtering."""
    user = _create_user(db_session, "notif_user")

    # Create notifications
    n1 = notification_service.create_notification(
        db=db_session,
        user_id=user.id,
        title="High Match Found",
        message="Senior Backend Engineer role matches your profile 94%",
        category=NotificationCategory.MATCH.value,
    )
    n2 = notification_service.create_notification(
        db=db_session,
        user_id=user.id,
        title="Interview Scheduled",
        message="Technical round with Stripe tomorrow at 3 PM",
        category=NotificationCategory.INTERVIEW.value,
    )

    # List all
    all_notifs = notification_service.list_notifications(db=db_session, user=user)
    assert all_notifs.total == 2
    assert all_notifs.unread_count == 2
    # Verify newest first
    assert all_notifs.items[0].id == n2.id
    assert all_notifs.items[1].id == n1.id

    # Filter by is_read=False
    unread_only = notification_service.list_notifications(
        db=db_session, user=user, is_read=False
    )
    assert unread_only.total == 2

    # Filter by is_read=True
    read_only = notification_service.list_notifications(
        db=db_session, user=user, is_read=True
    )
    assert read_only.total == 0


def test_notification_mark_as_read_and_unread_count(db_session: Session):
    """Tests marking individual and all notifications as read."""
    user = _create_user(db_session, "read_user")

    n1 = notification_service.create_notification(
        db=db_session, user_id=user.id, title="Alert 1", message="Msg 1"
    )
    n2 = notification_service.create_notification(
        db=db_session, user_id=user.id, title="Alert 2", message="Msg 2"
    )

    assert notification_service.get_unread_count(db=db_session, user=user) == 2

    # Mark single as read
    marked = notification_service.mark_as_read(
        db=db_session, user=user, notification_id=n1.id
    )
    assert marked.is_read is True
    assert notification_service.get_unread_count(db=db_session, user=user) == 1

    # Mark all remaining as read
    marked_count = notification_service.mark_all_as_read(db=db_session, user=user)
    assert marked_count == 1
    assert notification_service.get_unread_count(db=db_session, user=user) == 0


def test_notification_deletion(db_session: Session):
    """Deleting a notification removes it from database."""
    user = _create_user(db_session, "del_notif_user")

    n = notification_service.create_notification(
        db=db_session, user_id=user.id, title="To Delete", message="Msg"
    )

    notification_service.delete_notification(
        db=db_session, user=user, notification_id=n.id
    )
    assert notification_service.get_unread_count(db=db_session, user=user) == 0

    with pytest.raises(NotFoundError):
        notification_service.mark_as_read(db=db_session, user=user, notification_id=n.id)


def test_notification_multi_tenant_isolation(db_session: Session):
    """User B cannot view or modify User A's notifications."""
    user_a = _create_user(db_session, "notif_a")
    user_b = _create_user(db_session, "notif_b")

    n_a = notification_service.create_notification(
        db=db_session, user_id=user_a.id, title="Private A", message="A only"
    )

    # User B should see 0 notifications
    b_list = notification_service.list_notifications(db=db_session, user=user_b)
    assert b_list.total == 0

    # User B cannot mark A's notification as read
    with pytest.raises(NotFoundError):
        notification_service.mark_as_read(
            db=db_session, user=user_b, notification_id=n_a.id
        )

    # User B cannot delete A's notification
    with pytest.raises(NotFoundError):
        notification_service.delete_notification(
            db=db_session, user=user_b, notification_id=n_a.id
        )


def test_user_preferences_initialization_and_update(db_session: Session):
    """Ensures defaults are created upon first lookup and preferences update accurately."""
    user = _create_user(db_session, "pref_user")

    # 1. Defaults
    pref = digest_service.get_or_create_user_preferences(db=db_session, user=user)
    assert pref.digest_enabled is True
    assert pref.digest_time == "22:00"
    assert pref.preferred_work_modes == []
    assert pref.min_desired_salary is None

    # 2. Update
    updated = digest_service.update_user_preferences(
        db=db_session,
        user=user,
        data=UserPreferenceUpdate(
            digest_enabled=False,
            digest_time="20:30",
            preferred_work_modes=["REMOTE", "HYBRID"],
            min_desired_salary=120000.0,
        ),
    )
    assert updated.digest_enabled is False
    assert updated.digest_time == "20:30"
    assert updated.preferred_work_modes == ["REMOTE", "HYBRID"]
    assert updated.min_desired_salary == 120000.0


def test_digest_content_generation_and_filtering(db_session: Session):
    """Verifies digest compiles jobs according to user modality and salary filters."""
    user = _create_user(db_session, "digest_content_user")

    # Set user preference: REMOTE only, min salary 100k
    digest_service.update_user_preferences(
        db=db_session,
        user=user,
        data=UserPreferenceUpdate(
            preferred_work_modes=["REMOTE"],
            min_desired_salary=100000.0,
        ),
    )

    # Job 1: Remote, $140k (Matches filter)
    j1 = Job(
        user_id=user.id,
        company_name="CloudCorp",
        title="Senior Python Engineer",
        normalized_title="senior python engineer",
        location="Remote",
        work_mode="REMOTE",
        salary_currency="$",
        salary_min=130000.0,
        salary_max=160000.0,
        job_url="https://cloudcorp.io/careers/1",
        is_duplicate=False,
    )
    # Job 2: On-Site, $180k (Fails modality filter)
    j2 = Job(
        user_id=user.id,
        company_name="BankCorp",
        title="Java Developer",
        normalized_title="java developer",
        work_mode="ON_SITE",
        salary_min=180000.0,
        salary_max=200000.0,
        is_duplicate=False,
    )
    db_session.add_all([j1, j2])
    db_session.flush()

    resume = Resume(
        user_id=user.id,
        file_name="res.txt",
        file_path="/res.txt",
        extracted_text="Python Senior Developer",
    )
    db_session.add(resume)
    db_session.flush()

    # Link match for j1
    m1 = JobMatch(
        user_id=user.id,
        job_id=j1.id,
        resume_id=resume.id,
        overall_match_score=91.0,
        skill_score=90.0,
        experience_score=92.0,
        semantic_score=91.0,
        matched_skills=["Python", "FastAPI"],
        missing_required_skills=[],
        missing_preferred_skills=[],
        explanation_summary="Excellent fit",
    )
    db_session.add(m1)
    db_session.commit()

    # Generate preview
    preview = digest_service.generate_digest_content(db=db_session, user=user)

    assert preview.recipient_email == user.email
    assert preview.total_jobs_evaluated == 1  # Only j1 met the REMOTE modality filter
    assert preview.top_matches_count == 1
    assert preview.top_matches[0].company_name == "CloudCorp"
    assert preview.top_matches[0].match_score == 91.0
    assert "CloudCorp" in preview.html_content
    assert "91% Match" in preview.html_content
    assert "CloudCorp" in preview.text_content


def test_digest_dispatch_and_audit_record(db_session: Session):
    """Verifies that dispatching a digest creates DailyDigest and Notification records."""
    user = _create_user(db_session, "dispatch_user")

    res = digest_service.dispatch_digest_for_user(db=db_session, user=user)
    assert res.success is True
    assert res.digest_id is not None
    assert res.recipient_email == user.email

    # Check DailyDigest row in DB
    digest_rec = db_session.scalar(
        select(DailyDigest).where(DailyDigest.id == res.digest_id)
    )
    assert digest_rec is not None
    assert digest_rec.user_id == user.id
    assert digest_rec.status == "SENT"

    # Check in-app notification was triggered
    notif = db_session.scalar(
        select(Notification).where(
            Notification.user_id == user.id, Notification.category == "DIGEST"
        )
    )
    assert notif is not None
    assert "Daily Job Digest Dispatched" in notif.title

    # Check history listing
    history = digest_service.list_digest_history(db=db_session, user=user)
    assert history.total >= 1
    assert history.items[0].id == res.digest_id


def test_digest_dispatch_respects_disabled_preference(db_session: Session):
    """If user preference has digest_enabled=False, normal dispatch skips unless forced."""
    user = _create_user(db_session, "disabled_pref_user")

    digest_service.update_user_preferences(
        db=db_session,
        user=user,
        data=UserPreferenceUpdate(digest_enabled=False),
    )

    # 1. Normal dispatch -> Disabled
    normal_res = digest_service.dispatch_digest_for_user(
        db=db_session, user=user, force=False
    )
    assert normal_res.success is False
    assert normal_res.delivery_status == "DISABLED"

    # 2. Forced dispatch -> Succeeds
    force_res = digest_service.dispatch_digest_for_user(
        db=db_session, user=user, force=True
    )
    assert force_res.success is True
    assert force_res.digest_id is not None


def test_batch_scheduled_digest_dispatcher(db_session: Session):
    """Verifies batch dispatch to all users who have daily digest enabled."""
    user1 = _create_user(db_session, "batch_user_1")
    user2 = _create_user(db_session, "batch_user_2")
    user3 = _create_user(db_session, "batch_user_3")

    # Disable for user 3
    digest_service.update_user_preferences(
        db=db_session, user=user3, data=UserPreferenceUpdate(digest_enabled=False)
    )

    batch_res = digest_service.dispatch_scheduled_daily_digests(db=db_session)
    assert batch_res["dispatched"] >= 2
    assert batch_res["failed"] == 0


def test_api_notifications_and_digest_routes(client: TestClient, db_session: Session):
    """Full HTTP API test of notification and digest endpoints."""
    # 1. Register & Login
    email = f"api_notif_digest_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.scalar(select(User).where(User.email == email))

    # 2. Create notification directly
    notif = notification_service.create_notification(
        db=db_session,
        user_id=user.id,
        title="Welcome to AI Job Intel",
        message="Your account is ready.",
        category="SYSTEM",
    )

    # 3. GET /api/v1/notifications/unread-count
    count_resp = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] == 1

    # 4. GET /api/v1/notifications
    list_resp = client.get("/api/v1/notifications", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 5. PATCH /api/v1/notifications/{id}/read
    read_resp = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # 6. POST /api/v1/notifications/mark-all-read
    mark_all_resp = client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert mark_all_resp.status_code == 200
    assert mark_all_resp.json()["success"] is True

    # 7. GET & PATCH /api/v1/settings
    settings_get = client.get("/api/v1/settings", headers=headers)
    assert settings_get.status_code == 200
    assert settings_get.json()["digest_enabled"] is True

    settings_patch = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"digest_time": "21:30", "preferred_work_modes": ["REMOTE"]},
    )
    assert settings_patch.status_code == 200
    assert settings_patch.json()["digest_time"] == "21:30"
    assert settings_patch.json()["preferred_work_modes"] == ["REMOTE"]

    # 8. GET /api/v1/digest/preview
    prev_resp = client.get("/api/v1/digest/preview", headers=headers)
    assert prev_resp.status_code == 200
    assert prev_resp.json()["recipient_email"] == email

    # 9. POST /api/v1/digest/trigger
    trig_resp = client.post("/api/v1/digest/trigger", headers=headers)
    assert trig_resp.status_code == 200
    assert trig_resp.json()["success"] is True

    # 10. GET /api/v1/digest/history
    hist_resp = client.get("/api/v1/digest/history", headers=headers)
    assert hist_resp.status_code == 200
    assert hist_resp.json()["total"] >= 1

    # 11. DELETE /api/v1/notifications/{id}
    del_resp = client.delete(f"/api/v1/notifications/{notif.id}", headers=headers)
    assert del_resp.status_code == 204
