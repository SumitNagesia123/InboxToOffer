import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.job import Job, JobSkill
from app.models.match import JobMatch
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.models.user import User
from app.services.matching.matching_engine import matching_engine
from app.services.matching.matching_service import matching_service


def test_skills_matching_scoring():
    """Tests skill evaluation with required and preferred skill sets."""
    candidate_skills = ["Python", "FastAPI", "Docker", "PostgreSQL"]

    # 1. 100% Match
    score, matched, missing_req, missing_pref = matching_engine.evaluate_skills(
        candidate_skills=candidate_skills,
        job_required_skills=["Python", "FastAPI"],
        job_preferred_skills=["Docker"],
    )
    assert score == 100.0
    assert len(matched) == 3
    assert len(missing_req) == 0
    assert len(missing_pref) == 0

    # 2. Missing preferred
    score, matched, missing_req, missing_pref = matching_engine.evaluate_skills(
        candidate_skills=candidate_skills,
        job_required_skills=["Python", "FastAPI"],
        job_preferred_skills=["Kubernetes", "AWS"],
    )
    assert score == 75.0  # (0.75 * 1.0 + 0.25 * 0.0) * 100
    assert "Kubernetes" in missing_pref
    assert "AWS" in missing_pref

    # 3. Missing required
    score, matched, missing_req, missing_pref = matching_engine.evaluate_skills(
        candidate_skills=candidate_skills,
        job_required_skills=["Python", "Rust"],
        job_preferred_skills=["Docker"],
    )
    assert score < 70.0
    assert "Rust" in missing_req


def test_experience_matching_scoring():
    """Tests experience alignment under various candidate vs requirement scenarios."""
    # 1. Candidate exceeds minimum
    assert matching_engine.evaluate_experience(candidate_years=6.0, min_years=4, max_years=8) == 100.0

    # 2. Candidate below minimum
    score = matching_engine.evaluate_experience(candidate_years=2.0, min_years=4, max_years=None)
    assert score == 50.0  # (2 / 4) * 100

    # 3. Job has no minimum experience
    assert matching_engine.evaluate_experience(candidate_years=2.0, min_years=None, max_years=None) == 100.0


def test_semantic_relevance_scoring():
    """Tests semantic alignment between resume and job description."""
    resume_text = (
        "Senior Python Engineer specializing in cloud-native microservices with FastAPI, "
        "PostgreSQL, Docker, and Kubernetes on AWS."
    )
    job_desc = "Looking for a Senior Python Developer to build cloud microservices on AWS."

    high_score = matching_engine.evaluate_semantic_relevance(
        job_title="Senior Python Engineer",
        job_description=job_desc,
        resume_text=resume_text,
    )
    assert high_score >= 60.0

    low_score = matching_engine.evaluate_semantic_relevance(
        job_title="Registered Nurse (ICU)",
        job_description="Provide critical patient care in clinical ICU hospital unit.",
        resume_text=resume_text,
    )
    assert low_score < high_score


def test_overall_match_and_explainability_generation():
    """Verifies that overall match combines weights and generates human-readable explanations."""
    result = matching_engine.calculate_match(
        candidate_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        candidate_years=5.0,
        resume_text="Senior Python backend engineer with FastAPI and Docker microservices.",
        job_title="Senior Backend Engineer",
        job_description="Build distributed systems with Python, FastAPI, and Docker on AWS.",
        job_min_exp=4,
        job_max_exp=7,
        job_required_skills=["Python", "FastAPI"],
        job_preferred_skills=["AWS"],
    )

    assert result.overall_match_score >= 70.0
    assert "Senior" in result.explanation_summary or "match" in result.explanation_summary.lower()
    assert "Python" in result.matched_skills


def _get_or_create_skill(db: Session, name: str, normalized_name: str, category: str = "Technical") -> Skill:
    existing = db.scalar(select(Skill).where(Skill.normalized_name == normalized_name))
    if existing:
        return existing
    skill = Skill(name=name, normalized_name=normalized_name, category=category)
    db.add(skill)
    db.flush()
    return skill


def test_matching_service_and_upsert_flow(db_session: Session):
    """Verifies end-to-end database matching and idempotent upserting."""
    user = User(
        email=f"match_user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("pw123"),
        full_name="Match Tester",
    )
    db_session.add(user)
    db_session.flush()

    # Get or create Skill master records
    py_skill = _get_or_create_skill(db_session, "Python", "python", "Programming Language")
    fastapi_skill = _get_or_create_skill(db_session, "FastAPI", "fastapi", "Framework")

    # Create Resume
    resume = Resume(
        user_id=user.id,
        file_name="resume.pdf",
        file_path="/uploads/resume.pdf",
        extracted_text="Python Backend Engineer with 5 years experience in FastAPI and databases.",
        total_experience_years=5.0,
    )
    db_session.add(resume)
    db_session.flush()

    # Link Resume Skills
    db_session.add(ResumeSkill(resume_id=resume.id, skill_id=py_skill.id, years_experience=5.0))
    db_session.add(ResumeSkill(resume_id=resume.id, skill_id=fastapi_skill.id, years_experience=3.0))

    # Create Job
    job = Job(
        user_id=user.id,
        company_name="TechCorp",
        title="Python Developer",
        normalized_title="python developer",
        min_experience_years=3,
        job_description="Seeking a Python Developer skilled in FastAPI.",
        is_duplicate=False,
    )
    db_session.add(job)
    db_session.flush()

    # Link Job Skills
    db_session.add(JobSkill(job_id=job.id, skill_id=py_skill.id, is_required=True))
    db_session.add(JobSkill(job_id=job.id, skill_id=fastapi_skill.id, is_required=False))
    db_session.commit()

    # 1. First calculation
    match_res = matching_service.match_job_for_user(db=db_session, user=user, job_id=job.id)
    assert match_res.overall_match_score >= 80.0
    assert "Python" in match_res.matched_skills
    match_id = match_res.id

    # 2. Recalculation (idempotent upsert, same row ID)
    recalculated = matching_service.match_job_for_user(db=db_session, user=user, job_id=job.id)
    assert recalculated.id == match_id


def test_matching_user_isolation(db_session: Session):
    """Verifies that User A cannot calculate or view matches for User B's jobs."""
    user_a = User(email=f"user_a_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User A")
    user_b = User(email=f"user_b_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw", full_name="User B")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    # User A Job
    job_a = Job(
        user_id=user_a.id,
        company_name="Alpha",
        title="Engineer",
        normalized_title="engineer",
        is_duplicate=False,
    )
    # User B Resume
    resume_b = Resume(
        user_id=user_b.id,
        file_name="b.pdf",
        file_path="/b.pdf",
        extracted_text="Resume text B",
    )
    db_session.add_all([job_a, resume_b])
    db_session.commit()

    # User B attempting to match User A's job must fail with NotFoundError
    from app.core.errors import NotFoundError
    with pytest.raises(NotFoundError):
        matching_service.match_job_for_user(db=db_session, user=user_b, job_id=job_a.id)


def test_api_matching_routes(client: TestClient, db_session: Session):
    """Tests the full API match workflow: compute-all, compute single, list matches with filters."""
    # 1. Setup User
    email = f"api_match_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.scalar(select(User).where(User.email == email))

    # 2. Add Resume
    resume = Resume(
        user_id=user.id,
        file_name="resume.txt",
        file_path="/path/resume.txt",
        extracted_text="Experienced Full Stack Software Engineer proficient in Python, FastAPI, and React.",
        total_experience_years=5.0,
    )
    db_session.add(resume)
    db_session.flush()

    # 3. Add Jobs (Job 1: High Match, Job 2: Low Match)
    j1 = Job(
        user_id=user.id,
        company_name="Innovate",
        title="Python Backend Engineer",
        normalized_title="python backend engineer",
        job_description="Python, FastAPI, and PostgreSQL microservices.",
        min_experience_years=3,
        is_duplicate=False,
    )
    j2 = Job(
        user_id=user.id,
        company_name="BioMed",
        title="Clinical Trial Specialist",
        normalized_title="clinical trial specialist",
        job_description="Oncology clinical trial coordinator and patient management.",
        min_experience_years=5,
        is_duplicate=False,
    )
    db_session.add_all([j1, j2])
    db_session.commit()

    # 4. Trigger Batch Match via API
    batch_resp = client.post("/api/v1/matches/compute-all", headers=headers)
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_jobs_evaluated"] == 2
    assert batch_data["total_matches_created"] == 2

    # 5. List Matches via API
    list_resp = client.get("/api/v1/matches", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 2
    # Ranked order: first item should have higher score than second
    assert list_data["items"][0]["overall_match_score"] >= list_data["items"][1]["overall_match_score"]

    # 6. Single Job Match Detail
    detail_resp = client.get(f"/api/v1/matches/{j1.id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["job_title"] == "Python Backend Engineer"
    assert detail_data["overall_match_score"] >= 60.0
    assert len(detail_data["explanation_summary"]) > 10
