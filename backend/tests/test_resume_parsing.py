import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.models.user import User
from app.schemas.resume import ParsedResumeData
from app.services.resume.parser import resume_parser
from app.services.resume.resume_service import resume_service


SAMPLE_RESUME_TEXT = """# Emily Watson
emily.watson@example.com | (555) 234-5678 | Seattle, WA
https://linkedin.com/in/emily-watson | https://github.com/emilywatson

## Summary
Passionate Lead Backend Engineer with 7+ years of experience designing cloud-native distributed microservices.

## Experience
Lead Backend Engineer at CloudTech Systems (2020 - Present)
Architected scalable event-driven services using Python, FastAPI, Kafka, and Redis.
Improved throughput by 40% using asynchronous processing.

Senior Software Engineer at DataForge Labs (2017 - 2020)
Built data ingestion pipelines using Python, PostgreSQL, and Docker deployed on AWS.
Integrated CI/CD automation and automated unit testing suites.

## Education
University of Washington
Bachelor of Science in Computer Science, 2017
GPA: 3.8

## Technical Skills
Python, FastAPI, Django, PostgreSQL, Redis, Kafka, Docker, Kubernetes, AWS, Git, CI/CD
"""


def test_contact_information_extraction():
    """Verifies that regex and heuristic extractors capture contact info and URLs."""
    contact = resume_parser.extract_contact_info(SAMPLE_RESUME_TEXT)

    assert contact.name == "Emily Watson"
    assert contact.email == "emily.watson@example.com"
    assert contact.phone == "(555) 234-5678"
    assert "Seattle" in (contact.location or "")
    assert "linkedin.com/in/emily-watson" in (contact.linkedin_url or "")
    assert "github.com/emilywatson" in (contact.github_url or "")


def test_work_experience_and_duration_calculation():
    """Verifies parsing of job titles, companies, dates, and total experience calculation."""
    sections = resume_parser.extract_sections(SAMPLE_RESUME_TEXT)
    exp_text = sections.get("EXPERIENCE", "")

    items, total_years = resume_parser.extract_work_experience(exp_text)

    assert len(items) == 2
    assert total_years is not None
    assert total_years >= 6.0  # (2020-now) + (2020-2017)

    # Check first role
    assert any("Lead Backend Engineer" in item.role for item in items)
    assert any("CloudTech Systems" in item.company for item in items)

    # Check skills tagged to work experience
    lead_item = [i for i in items if "Lead Backend Engineer" in i.role][0]
    assert "FastAPI" in lead_item.skills_used or "Python" in lead_item.skills_used


def test_education_parsing():
    """Verifies parsing of university, degree, graduation year, and GPA."""
    sections = resume_parser.extract_sections(SAMPLE_RESUME_TEXT)
    edu_text = sections.get("EDUCATION", "")

    edu_items = resume_parser.extract_education(edu_text)
    assert len(edu_items) >= 1

    item = edu_items[0]
    assert "University of Washington" in item.institution
    assert item.graduation_year == 2017
    assert item.gpa == "3.8"
    assert "Bachelor" in (item.degree or "")


def test_skill_taxonomy_extraction():
    """Verifies that recognized skills are scanned, extracted, and categorized."""
    skills = resume_parser.extract_skills(SAMPLE_RESUME_TEXT)
    skill_names = [s.name for s in skills]

    assert "Python" in skill_names
    assert "FastAPI" in skill_names
    assert "PostgreSQL" in skill_names
    assert "Docker" in skill_names
    assert "AWS" in skill_names

    # Check categories
    python_skill = [s for s in skills if s.name == "Python"][0]
    assert python_skill.category == "Programming Language"


def test_parse_and_persist_resume_flow(db_session: Session):
    """Verifies end-to-end resume structuring and database persistence into resumes and resume_skills."""
    user = User(
        email=f"parsed_user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("secure123"),
        full_name="Emily Watson",
    )
    db_session.add(user)
    db_session.flush()

    resume = Resume(
        user_id=user.id,
        file_name="emily_watson.txt",
        file_path="/uploads/test.txt",
        extracted_text=SAMPLE_RESUME_TEXT,
    )
    db_session.add(resume)
    db_session.commit()

    # Trigger structuring service
    structured = resume_service.parse_and_persist_resume(db=db_session, user=user)

    assert structured.user_id == user.id
    assert structured.skills_count >= 5
    assert structured.experience_count == 2
    assert structured.total_experience_years is not None
    assert structured.total_experience_years >= 6.0

    # Verify DB state
    db_session.refresh(resume)
    assert resume.total_experience_years is not None
    assert resume.education_summary is not None
    assert len(resume.education_summary.get("items", [])) >= 1

    # Verify resume_skills records
    saved_skills = db_session.scalars(
        select(ResumeSkill).where(ResumeSkill.resume_id == resume.id)
    ).all()
    assert len(saved_skills) >= 5


def test_api_resume_parsing_and_isolation(client: TestClient, db_session: Session):
    """Tests POST /api/v1/resumes/parse and GET /api/v1/resumes/me/structured with tenant isolation."""
    # 1. Setup User A
    email_a = f"parse_api_a_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!"})
    login_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Setup User B
    email_b = f"parse_api_b_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!"})
    login_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. User A uploads resume
    files = {"file": ("resume.txt", io.BytesIO(SAMPLE_RESUME_TEXT.encode("utf-8")), "text/plain")}
    up_resp = client.post("/api/v1/resumes/upload", headers=headers_a, files=files)
    assert up_resp.status_code == 201

    # 3. User A triggers parsing
    parse_resp = client.post("/api/v1/resumes/parse", headers=headers_a)
    assert parse_resp.status_code == 200
    data = parse_resp.json()
    assert data["parsed_data"]["contact_info"]["name"] == "Emily Watson"
    assert data["skills_count"] >= 5
    assert data["experience_count"] == 2

    # 4. User A gets structured profile
    struct_resp = client.get("/api/v1/resumes/me/structured", headers=headers_a)
    assert struct_resp.status_code == 200
    struct_data = struct_resp.json()
    assert struct_data["total_experience_years"] is not None

    # 5. User B isolation check: User B has no resume uploaded
    user_b_resp = client.get("/api/v1/resumes/me/structured", headers=headers_b)
    assert user_b_resp.status_code == 404
