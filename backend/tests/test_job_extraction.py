import uuid
from datetime import datetime, timezone
import pytest
from fastapi import status
from sqlalchemy import select

from app.models.company import Company
from app.models.email import Email
from app.models.job import Job, JobSkill
from app.models.user import User
from app.schemas.job import EmploymentType, WorkMode
from app.services.nlp.extractor import job_extractor


def test_salary_extraction_ranges():
    """Verify salary extraction accurately captures currency and min/max bounds."""
    # USD Range with k
    text1 = "We offer a competitive compensation of $130k - $160k per year plus equity."
    curr1, min1, max1 = job_extractor.extract_salary(text1)
    assert curr1 == "USD"
    assert min1 == 130000.0
    assert max1 == 160000.0

    # USD Full digits
    text2 = "Salary range: $120,000 - $150,000 / year"
    curr2, min2, max2 = job_extractor.extract_salary(text2)
    assert curr2 == "USD"
    assert min2 == 120000.0
    assert max2 == 150000.0

    # INR in LPA
    text3 = "Expected CTC: 15 - 25 LPA based on experience."
    curr3, min3, max3 = job_extractor.extract_salary(text3)
    assert curr3 == "INR"
    assert min3 == 1500000.0
    assert max3 == 2500000.0

    # EUR
    text4 = "Base compensation: €70,000 - €90,000"
    curr4, min4, max4 = job_extractor.extract_salary(text4)
    assert curr4 == "EUR"
    assert min4 == 70000.0
    assert max4 == 90000.0


def test_no_hallucination_salary_and_experience():
    """Verify missing salary and experience strictly default to None without hallucination."""
    clean_text = "Looking for a passionate engineer to join our fast-growing startup team."
    curr, min_s, max_s = job_extractor.extract_salary(clean_text)
    assert curr is None
    assert min_s is None
    assert max_s is None

    min_e, max_e = job_extractor.extract_experience(clean_text)
    assert min_e is None
    assert max_e is None


def test_experience_extraction_bounds():
    """Verify experience ranges and minimums are parsed correctly."""
    # Range
    text1 = "Candidate should possess 3-5 years of hands-on software development experience."
    min1, max1 = job_extractor.extract_experience(text1)
    assert min1 == 3
    assert max1 == 5

    # Plus
    text2 = "Requirements: 5+ years of building backend microservices."
    min2, max2 = job_extractor.extract_experience(text2)
    assert min2 == 5
    assert max2 is None

    # Minimum
    text3 = "Minimum 2 years experience with Python."
    min3, max3 = job_extractor.extract_experience(text3)
    assert min3 == 2
    assert max3 is None


def test_work_mode_and_employment_type():
    """Verify work mode and employment type classification."""
    # Remote Full-time
    loc1, wm1 = job_extractor.extract_location_and_work_mode("This is a 100% remote position based anywhere.")
    et1 = job_extractor.extract_employment_type("This is a full-time permanent role.")
    assert wm1 == WorkMode.REMOTE
    assert loc1 == "Remote"
    assert et1 == EmploymentType.FULL_TIME

    # Hybrid Contract
    loc2, wm2 = job_extractor.extract_location_and_work_mode("Location: New York, NY. Hybrid schedule 3 days in office.")
    et2 = job_extractor.extract_employment_type("6-month contract opportunity.")
    assert wm2 == WorkMode.HYBRID
    assert "New York" in (loc2 or "")
    assert et2 == EmploymentType.CONTRACT


def test_skills_and_url_extraction():
    """Verify technical skill taxonomy extraction and clean application link detection."""
    body = """
    About the role:
    We are seeking a Senior Backend Engineer.
    Must-have skills: Python, FastAPI, PostgreSQL, Docker, AWS.
    Nice to have: React, Kubernetes.
    Apply here: https://boards.greenhouse.io/acmecorp/jobs/5678?utm_source=linkedin
    """
    links = ["https://boards.greenhouse.io/acmecorp/jobs/5678"]

    req_skills, pref_skills = job_extractor.extract_skills(body)
    assert "Python" in req_skills
    assert "FastAPI" in req_skills
    assert "PostgreSQL" in req_skills
    assert "Docker" in req_skills
    assert "AWS" in req_skills
    assert "Kubernetes" in pref_skills

    job_url = job_extractor.extract_job_url(links)
    assert job_url == "https://boards.greenhouse.io/acmecorp/jobs/5678"


def test_extract_and_persist_job_flow(client, db_session):
    """Verify job extraction API, database persistence, and foreign key relations."""
    pwd = "SecurePassword123!"
    email_addr = f"job_extract_user_{uuid.uuid4().hex[:8]}@example.com"

    client.post("/api/v1/auth/register", json={"email": email_addr, "password": pwd})
    user = db_session.scalar(select(User).where(User.email == email_addr.lower()))
    token = client.post("/api/v1/auth/login", json={"email": email_addr, "password": pwd}).json()["access_token"]

    # Ingest a job email
    raw_email = Email(
        user_id=user.id,
        gmail_message_id=f"msg_job_{uuid.uuid4().hex[:8]}",
        sender="careers@stripe.com",
        recipient=user.email,
        subject="Senior Backend Engineer at Stripe - Remote",
        body_text="""
        Stripe is hiring a Senior Backend Engineer.
        Location: Remote
        Compensation: $140k - $180k per year
        Experience: 4-7 years
        Requirements: Python, FastAPI, PostgreSQL, Docker, AWS.
        Apply online: https://stripe.com/jobs/senior-backend-engineer
        """,
        received_at=datetime.now(timezone.utc),
        category="JOB",
        processed_status="CLASSIFIED",
    )
    db_session.add(raw_email)
    db_session.commit()
    db_session.refresh(raw_email)

    # 1. Trigger extraction via API
    resp = client.post(
        f"/api/v1/jobs/extract/{raw_email.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    job_data = resp.json()
    assert job_data["company_name"] == "Stripe"
    assert "Backend Engineer" in job_data["title"]
    assert job_data["work_mode"] == "REMOTE"
    assert job_data["salary_min"] == 140000.0
    assert job_data["salary_max"] == 180000.0
    assert job_data["min_experience_years"] == 4
    assert job_data["max_experience_years"] == 7
    assert "Python" in job_data["required_skills"]
    assert "PostgreSQL" in job_data["required_skills"]

    # 2. Verify in database
    db_job = db_session.scalar(select(Job).where(Job.source_email_id == raw_email.id))
    assert db_job is not None
    assert db_job.user_id == user.id
    assert db_job.company_id is not None
    assert len(db_job.job_skills) >= 3

    # Check Company record created
    db_company = db_session.get(Company, db_job.company_id)
    assert db_company is not None
    assert db_company.normalized_name == "stripe"

    # Check Email status updated
    db_session.refresh(raw_email)
    assert raw_email.processed_status == "EXTRACTED"

    # 3. List jobs endpoint
    list_resp = client.get("/api/v1/jobs?work_mode=REMOTE", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.json()["total"] == 1

    # 4. Get single job endpoint
    detail_resp = client.get(f"/api/v1/jobs/{db_job.id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == status.HTTP_200_OK
    assert detail_resp.json()["id"] == str(db_job.id)


def test_job_extraction_user_isolation(client, db_session):
    """Verify User A cannot access or extract jobs from User B's emails."""
    pwd = "SecurePassword123!"
    email_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    email_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"

    client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd})
    user_a = db_session.scalar(select(User).where(User.email == email_a.lower()))
    user_b = db_session.scalar(select(User).where(User.email == email_b.lower()))

    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pwd}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pwd}).json()["access_token"]

    # Ingest job email for User A
    email_a_record = Email(
        user_id=user_a.id,
        gmail_message_id=f"msg_a_{uuid.uuid4().hex[:6]}",
        sender="careers@google.com",
        recipient=user_a.email,
        subject="Staff Engineer at Google",
        body_text="Google is hiring a Staff Engineer.",
        received_at=datetime.now(timezone.utc),
        category="JOB",
        processed_status="CLASSIFIED",
    )
    db_session.add(email_a_record)
    db_session.commit()
    db_session.refresh(email_a_record)

    # User B tries to extract from User A's email -> 404
    resp_b_extract = client.post(
        f"/api/v1/jobs/extract/{email_a_record.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b_extract.status_code == status.HTTP_404_NOT_FOUND

    # User A extracts job
    resp_a_extract = client.post(
        f"/api/v1/jobs/extract/{email_a_record.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a_extract.status_code == status.HTTP_200_OK
    job_id = resp_a_extract.json()["id"]

    # User B cannot view User A's job -> 404
    resp_b_view = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b_view.status_code == status.HTTP_404_NOT_FOUND

    # User B's job list is empty
    list_b = client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert list_b["total"] == 0
