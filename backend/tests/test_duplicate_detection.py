import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.services.auth_service import auth_service
from app.services.job.deduplication_engine import (
    calculate_description_similarity,
    deduplication_engine,
    normalize_company_name,
    normalize_job_title,
    normalize_job_url,
)
from app.services.job.deduplication_service import job_deduplication_service


def test_url_normalization_and_exact_match():
    """Verifies that tracking parameters, fragments, and variations normalize to exact canonical URLs."""
    url1 = "https://www.linkedin.com/jobs/view/998877?utm_source=feed&trk=job_alert&refId=abc1234"
    url2 = "https://linkedin.com/jobs/view/998877/?refId=xyz999&utm_medium=email"
    url3 = "https://linkedin.com/jobs/view/998877#apply"

    norm1 = normalize_job_url(url1)
    norm2 = normalize_job_url(url2)
    norm3 = normalize_job_url(url3)

    assert norm1 == "https://linkedin.com/jobs/view/998877"
    assert norm1 == norm2
    assert norm2 == norm3

    # Compare jobs with identical URLs
    match = deduplication_engine.compare_jobs(
        candidate_url=url1,
        candidate_company="Acme Corp",
        candidate_title="Backend Engineer",
        candidate_description="Building high-scale Python microservices",
        candidate_location="San Francisco, CA",
        existing_url=url2,
        existing_company="Acme Inc",
        existing_title="Senior Backend Engineer",
        existing_description="Designing Python microservices",
        existing_location="San Francisco, CA",
    )
    assert match.is_duplicate is True
    assert match.confidence == 1.0
    assert match.match_method == "EXACT_URL"


def test_company_and_title_normalization():
    """Verifies string cleanup and token normalization across titles and company designations."""
    assert normalize_company_name("Google, Inc.") == "google"
    assert normalize_company_name("Amazon Web Services (AWS) LLC") == "amazon web"
    assert normalize_company_name("Databricks Technologies India Pvt. Ltd.") == "databricks india"

    assert normalize_job_title("Sr. Software Engineer [Remote]") == "senior software engineer"
    assert normalize_job_title("SWE - Backend (Req-12345)") == "software engineer back end"
    assert normalize_job_title("Staff Devops / SRE (Job ID: 9876)") == "staff devops engineer sre"


def test_title_and_company_fingerprint_matching():
    """Tests deduplication matching via normalized company and job title."""
    match = deduplication_engine.compare_jobs(
        candidate_url=None,
        candidate_company="Databricks, Inc.",
        candidate_title="Sr. Software Engineer [Remote]",
        candidate_description="Build distributed systems with Python and Spark.",
        candidate_location="Remote",
        existing_url=None,
        existing_company="Databricks",
        existing_title="Senior Software Engineer",
        existing_description="Lead the design of distributed data processing engines.",
        existing_location="Remote",
    )
    assert match.is_duplicate is True
    assert match.match_method == "TITLE_COMPANY_FINGERPRINT"
    assert match.confidence >= 0.85


def test_description_similarity_matching():
    """Tests TF-IDF description similarity for jobs with overlapping descriptions."""
    long_desc_1 = (
        "We are looking for a Senior Python Developer to join our Cloud Infrastructure team. "
        "You will design, develop, and deploy scalable microservices using FastAPI, Docker, and Kubernetes. "
        "Requirements include 5+ years of experience with Python, PostgreSQL, asynchronous programming, "
        "and building robust CI/CD deployment pipelines on AWS."
    )
    long_desc_2 = (
        "Join our Cloud Infrastructure team as a Backend Engineer (Python). "
        "In this role, you will design, develop, and deploy scalable microservices using FastAPI, Docker, and Kubernetes. "
        "Candidates should have at least 5 years of experience with Python, PostgreSQL, async programming, "
        "and implementing robust CI/CD pipelines in AWS cloud environments."
    )

    sim = calculate_description_similarity(long_desc_1, long_desc_2)
    assert sim >= 0.60

    match = deduplication_engine.compare_jobs(
        candidate_url="https://company.com/jobs/1",
        candidate_company="Stripe",
        candidate_title="Backend Engineer",
        candidate_description=long_desc_1,
        candidate_location="Remote",
        existing_url="https://different-source.com/stripe/123",
        existing_company="Stripe Technologies",
        existing_title="Python Developer",
        existing_description=long_desc_2,
        existing_location="Remote",
    )
    assert match.is_duplicate is True
    assert match.match_method in ("TITLE_COMPANY_FINGERPRINT", "DESCRIPTION_SIMILARITY")


def test_distinct_jobs_not_flagged_as_duplicate():
    """Verifies that non-matching jobs are correctly kept distinct."""
    match = deduplication_engine.compare_jobs(
        candidate_url="https://careers.google.com/jobs/1",
        candidate_company="Google",
        candidate_title="Senior Product Manager",
        candidate_description="Lead product vision and roadmap for Android ecosystem.",
        candidate_location="Mountain View, CA",
        existing_url="https://careers.google.com/jobs/2",
        existing_company="Google",
        existing_title="Senior Software Engineer",
        existing_description="Develop low-level C++ rendering engines for Chrome.",
        existing_location="Mountain View, CA",
    )
    assert match.is_duplicate is False
    assert match.confidence == 0.0


def test_canonical_job_enrichment_flow(db_session: Session):
    """Verifies that duplicate postings enrich the canonical root job with missing details."""
    user = User(
        email=f"dedup_user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Dedup Candidate",
    )
    db_session.add(user)
    db_session.flush()

    # 1. Canonical job without salary
    canonical_job = Job(
        user_id=user.id,
        company_name="Netflix",
        normalized_title="senior software engineer",
        title="Senior Software Engineer",
        work_mode="REMOTE",
        employment_type="FULL_TIME",
        salary_currency=None,
        salary_min=None,
        salary_max=None,
        is_duplicate=False,
    )
    db_session.add(canonical_job)
    db_session.flush()

    # 2. Duplicate posting with salary details
    duplicate_job = Job(
        user_id=user.id,
        company_name="Netflix, Inc.",
        normalized_title="senior software engineer",
        title="Sr. Software Engineer (Remote)",
        work_mode="REMOTE",
        employment_type="FULL_TIME",
        salary_currency="USD",
        salary_min=180000.0,
        salary_max=220000.0,
        job_url="https://netflix.com/jobs/123",
        is_duplicate=False,
    )
    db_session.add(duplicate_job)
    db_session.flush()

    # Link duplicate
    match = job_deduplication_service.check_and_link_duplicate(db_session, duplicate_job)
    assert match.is_duplicate is True
    assert duplicate_job.is_duplicate is True
    assert duplicate_job.canonical_job_id == canonical_job.id

    # Check enrichment
    db_session.refresh(canonical_job)
    assert canonical_job.salary_currency == "USD"
    assert canonical_job.salary_min == 180000.0
    assert canonical_job.salary_max == 220000.0
    assert canonical_job.job_url == "https://netflix.com/jobs/123"


def test_deduplication_user_isolation(db_session: Session):
    """Verifies that jobs belonging to different users are NEVER marked as duplicates of each other."""
    user_a = User(
        email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("pwd"),
        full_name="User A",
    )
    user_b = User(
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("pwd"),
        full_name="User B",
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    # Identical job for User A
    job_a = Job(
        user_id=user_a.id,
        company_name="Microsoft",
        title="Staff Engineer",
        normalized_title="staff engineer",
        job_url="https://careers.microsoft.com/job/100",
        is_duplicate=False,
    )
    # Identical job for User B
    job_b = Job(
        user_id=user_b.id,
        company_name="Microsoft",
        title="Staff Engineer",
        normalized_title="staff engineer",
        job_url="https://careers.microsoft.com/job/100",
        is_duplicate=False,
    )
    db_session.add_all([job_a, job_b])
    db_session.commit()

    match_b = job_deduplication_service.check_and_link_duplicate(db_session, job_b)
    assert match_b.is_duplicate is False
    assert job_b.is_duplicate is False
    assert job_b.canonical_job_id is None


def test_api_deduplication_routes(client: TestClient, db_session: Session):
    """Tests the /api/v1/jobs/deduplicate and /api/v1/jobs/{id}/duplicates API endpoints."""
    # Register and login user
    email_addr = f"api_dedup_{uuid.uuid4().hex[:6]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email_addr, "password": "Password123!", "full_name": "API Dedup User"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email_addr, "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch user model
    user = db_session.query(User).filter(User.email == email_addr).first()

    # Seed 3 jobs: Job 1 (Canonical), Job 2 (Duplicate of Job 1), Job 3 (Distinct)
    j1 = Job(
        user_id=user.id,
        company_name="Apple",
        title="iOS Engineer",
        normalized_title="ios engineer",
        job_url="https://apple.com/careers/ios-101",
        work_mode="ON_SITE",
    )
    j2 = Job(
        user_id=user.id,
        company_name="Apple Inc",
        title="iOS Engineer",
        normalized_title="ios engineer",
        job_url="https://apple.com/careers/ios-101?trk=email",
        work_mode="ON_SITE",
    )
    j3 = Job(
        user_id=user.id,
        company_name="Spotify",
        title="Data Engineer",
        normalized_title="data engineer",
        job_url="https://spotify.com/careers/data-202",
        work_mode="REMOTE",
    )
    db_session.add_all([j1, j2, j3])
    db_session.commit()

    # 1. Run batch deduplicate sweep
    dedup_resp = client.post("/api/v1/jobs/deduplicate", headers=headers)
    assert dedup_resp.status_code == 200
    data = dedup_resp.json()
    assert data["total_jobs"] == 3
    assert data["duplicates_identified"] == 1
    assert data["unique_canonical_jobs"] == 2

    # 2. Check duplicates endpoint for Job 1
    cluster_resp = client.get(f"/api/v1/jobs/{j1.id}/duplicates", headers=headers)
    assert cluster_resp.status_code == 200
    cluster_data = cluster_resp.json()
    assert cluster_data["duplicate_count"] == 1
    assert cluster_data["canonical_job"]["id"] == str(j1.id)
    assert cluster_data["duplicate_jobs"][0]["id"] == str(j2.id)

    # 3. List jobs with and without include_duplicates
    # Default (include_duplicates=False) -> Only canonical jobs
    list_resp = client.get("/api/v1/jobs", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    # With include_duplicates=True -> All 3 jobs
    list_all_resp = client.get("/api/v1/jobs?include_duplicates=true", headers=headers)
    assert list_all_resp.status_code == 200
    assert list_all_resp.json()["total"] == 3
