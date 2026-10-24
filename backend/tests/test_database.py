import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from app.database.session import SessionLocal, engine
from app.models import (
    Base,
    User,
    OAuthCredential,
    Email,
    Company,
    Skill,
    Job,
    JobSkill,
    Resume,
    ResumeSkill,
    JobMatch,
    Application,
    UserPreference,
    ProcessingRun,
    ProcessingError,
    Notification,
    DailyDigest,
)


def test_database_tables_exist():
    """Verify that all required tables are created in PostgreSQL."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    expected_tables = {
        "alembic_version",
        "users",
        "oauth_credentials",
        "emails",
        "companies",
        "skills",
        "jobs",
        "job_skills",
        "resumes",
        "resume_skills",
        "job_matches",
        "applications",
        "user_preferences",
        "processing_runs",
        "processing_errors",
        "notifications",
        "daily_digests",
    }

    missing_tables = expected_tables - existing_tables
    assert not missing_tables, f"Missing tables in PostgreSQL: {missing_tables}"


def test_database_crud_and_cascades():
    """Verify transactional CRUD and foreign key cascades on models."""
    db = SessionLocal()
    try:
        # 1. Create a user
        unique_email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=unique_email,
            hashed_password="mock_hashed_bcrypt_password",
            full_name="Test Candidate",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None
        assert user.email == unique_email

        # 2. Add an OAuth credential for the user
        oauth = OAuthCredential(
            user_id=user.id,
            provider="google",
            encrypted_access_token="encrypted_test_token",
            encrypted_refresh_token="encrypted_test_refresh_token",
            client_id="mock_client_id",
            scopes="https://www.googleapis.com/auth/gmail.readonly",
            expires_at=datetime.now(timezone.utc),
        )
        db.add(oauth)

        # 3. Add an ingested Email
        email_record = Email(
            user_id=user.id,
            gmail_message_id=f"msg_{uuid.uuid4().hex[:12]}",
            sender="jobs-noreply@linkedin.com",
            recipient=user.email,
            subject="Senior Python Developer Opportunity",
            body_text="We have a Senior Python Developer opening at Tech Corp.",
            received_at=datetime.now(timezone.utc),
            category="JOB",
            processed_status="PROCESSED",
        )
        db.add(email_record)
        db.commit()
        db.refresh(email_record)

        # 4. Add a Company and a Job
        company = Company(
            name="Tech Corp",
            normalized_name=f"tech_corp_{uuid.uuid4().hex[:6]}",
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        job = Job(
            user_id=user.id,
            source_email_id=email_record.id,
            company_id=company.id,
            company_name="Tech Corp",
            title="Senior Python Developer",
            normalized_title="senior python developer",
            location="Remote",
            work_mode="REMOTE",
            employment_type="FULL_TIME",
            salary_currency="USD",
            salary_min=130000,
            salary_max=160000,
            platform_source="LinkedIn",
            embedding=[0.1, 0.2, 0.3, 0.4],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        assert job.id is not None
        assert job.company_name == "Tech Corp"

        # 5. Add Skill and JobSkill
        skill = Skill(
            name=f"Python_{uuid.uuid4().hex[:4]}",
            normalized_name=f"python_{uuid.uuid4().hex[:4]}",
            category="Programming Languages",
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)

        job_skill = JobSkill(job_id=job.id, skill_id=skill.id, is_required=True)
        db.add(job_skill)

        # 6. Add Resume and ResumeSkill
        resume = Resume(
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resumes/resume.pdf",
            extracted_text="Python engineer with 5 years experience.",
            total_experience_years=5.0,
            embedding=[0.1, 0.2, 0.3, 0.4],
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

        resume_skill = ResumeSkill(
            resume_id=resume.id,
            skill_id=skill.id,
            years_experience=5.0,
        )
        db.add(resume_skill)

        # 7. Add JobMatch
        match = JobMatch(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            overall_match_score=92.5,
            skill_score=95.0,
            experience_score=90.0,
            semantic_score=92.0,
            matched_skills=["Python"],
            missing_required_skills=[],
            missing_preferred_skills=["Docker"],
            explanation_summary="Strong match for Python and experience level.",
        )
        db.add(match)

        # 8. Add User Preference
        preference = UserPreference(
            user_id=user.id,
            digest_enabled=True,
            digest_time="22:00",
            preferred_work_modes=["REMOTE"],
            min_desired_salary=120000,
        )
        db.add(preference)

        # 9. Add Application Tracker
        app = Application(
            user_id=user.id,
            job_id=job.id,
            status="APPLIED",
            applied_date=datetime.now(timezone.utc),
            notes="Applied via LinkedIn link",
        )
        db.add(app)

        # 10. Add Audit records (ProcessingRun, Notification, DailyDigest)
        run = ProcessingRun(
            user_id=user.id,
            status="COMPLETED",
            emails_fetched=10,
            jobs_extracted=2,
            duplicates_found=1,
        )
        db.add(run)

        notif = Notification(
            user_id=user.id,
            title="New High Match Job Found",
            message="Senior Python Developer at Tech Corp matches your profile 92.5%",
            category="MATCH",
        )
        db.add(notif)

        digest = DailyDigest(
            user_id=user.id,
            total_emails_processed=10,
            new_jobs_count=2,
            top_matches_count=1,
            recipient_email=user.email,
            status="SENT",
        )
        db.add(digest)
        db.commit()

        # 11. Query and verify relations
        queried_user = db.scalar(select(User).where(User.id == user.id))
        assert queried_user is not None
        assert len(queried_user.emails) == 1
        assert len(queried_user.jobs) == 1
        assert queried_user.resume is not None
        assert len(queried_user.job_matches) == 1
        assert queried_user.job_matches[0].overall_match_score == 92.5
        assert len(queried_user.applications) == 1
        assert queried_user.preference.digest_time == "22:00"
        assert len(queried_user.daily_digests) == 1
        assert len(queried_user.processing_runs) == 1

        # 12. Clean up test user (verifies cascade delete)
        db.delete(queried_user)
        db.commit()

        # Confirm cascade deletion across all linked tables
        assert db.scalar(select(OAuthCredential).where(OAuthCredential.user_id == user.id)) is None
        assert db.scalar(select(Job).where(Job.user_id == user.id)) is None
        assert db.scalar(select(Resume).where(Resume.user_id == user.id)) is None
        assert db.scalar(select(JobMatch).where(JobMatch.user_id == user.id)) is None
        assert db.scalar(select(Application).where(Application.user_id == user.id)) is None
        assert db.scalar(select(DailyDigest).where(DailyDigest.user_id == user.id)) is None
        assert db.scalar(select(ProcessingRun).where(ProcessingRun.user_id == user.id)) is None

    finally:
        db.close()


def test_unique_constraints_and_multi_user_isolation():
    """Verify unique constraints prevent duplicates within the same user."""
    db = SessionLocal()
    try:
        user_a = User(
            email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="hashed_pw_a",
            full_name="User A",
        )
        user_b = User(
            email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="hashed_pw_b",
            full_name="User B",
        )
        db.add_all([user_a, user_b])
        db.commit()

        # Both users can receive the same Gmail Message ID independently
        shared_msg_id = "gmail_msg_shared_12345"
        email_a = Email(
            user_id=user_a.id,
            gmail_message_id=shared_msg_id,
            sender="jobs@test.com",
            recipient=user_a.email,
            subject="Job Alert",
            received_at=datetime.now(timezone.utc),
        )
        email_b = Email(
            user_id=user_b.id,
            gmail_message_id=shared_msg_id,
            sender="jobs@test.com",
            recipient=user_b.email,
            subject="Job Alert",
            received_at=datetime.now(timezone.utc),
        )
        db.add_all([email_a, email_b])
        db.commit()

        # User A cannot insert duplicate of the same message_id
        duplicate_email_a = Email(
            user_id=user_a.id,
            gmail_message_id=shared_msg_id,
            sender="jobs@test.com",
            recipient=user_a.email,
            subject="Job Alert Duplicate",
            received_at=datetime.now(timezone.utc),
        )
        db.add(duplicate_email_a)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Clean up
        db.delete(user_a)
        db.delete(user_b)
        db.commit()
    finally:
        db.close()
