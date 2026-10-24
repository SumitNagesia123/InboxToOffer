import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.resume import Resume
from app.models.user import User
from app.services.resume.extractor import resume_extractor
from app.services.resume.resume_service import resume_service


def _generate_valid_sample_pdf(content: str) -> bytes:
    """Builds a well-formed PDF byte stream containing text stream."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({content}) Tj ET\n".encode("latin-1")
    length = len(stream_content)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"5 0 obj << /Length " + str(length).encode("ascii") + b" >> stream\n"
        + stream_content +
        b"endstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000262 00000 n \n"
        b"0000000335 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n460\n%%EOF"
    )
    return pdf


def test_text_cleaner_and_normalizer():
    """Verifies that text sanitization strips control codes, null bytes, and normalizes spacing."""
    dirty_text = "Jane\x00 Doe\r\n\r\n\r\nSenior Software\t\tEngineer\n\n\n\nSkills: Python, FastAPI\x0b"
    cleaned = resume_extractor.clean_text(dirty_text)

    assert "\x00" not in cleaned
    assert "\x0b" not in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "Senior Software Engineer" in cleaned
    assert "Skills: Python, FastAPI" in cleaned


def test_plain_text_and_markdown_resume_extraction():
    """Verifies extraction and metadata generation from Markdown and plain text files."""
    md_content = """# Alex Johnson - Staff Engineer
Email: alex@example.com | San Francisco, CA

## Summary
Experienced Backend Engineer with 8+ years architecting cloud-native distributed systems.

## Technical Skills
- Languages: Python, Go, TypeScript, SQL
- Technologies: FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis

## Experience
**Lead Software Engineer** at CloudScale Inc (2021 - Present)
- Designed and maintained high-throughput microservices processing 50M events daily.
""".encode("utf-8")

    res = resume_extractor.extract("alex_resume.md", md_content)
    assert res.page_count == 1
    assert "Alex Johnson - Staff Engineer" in res.clean_text
    assert "FastAPI, PostgreSQL" in res.clean_text
    assert res.character_count > 100
    assert res.word_count > 20
    assert res.text_preview.startswith("# Alex Johnson")


def test_pdf_resume_extraction():
    """Verifies text extraction from a valid binary PDF document."""
    pdf_bytes = _generate_valid_sample_pdf("Sarah Connor - Cybersecurity and Python Specialist")
    res = resume_extractor.extract("sarah_resume.pdf", pdf_bytes)

    assert res.page_count == 1
    assert "Sarah Connor" in res.clean_text
    assert "Cybersecurity and Python Specialist" in res.clean_text


def test_invalid_and_corrupt_files_validation():
    """Verifies error handling for unsupported formats, empty files, or corrupt buffers."""
    # 1. Unsupported extension
    with pytest.raises(ValidationError) as exc1:
        resume_extractor.extract("malicious.exe", b"binarycontenthere12345")
    assert "Unsupported resume file format" in str(exc1.value)

    # 2. Corrupt PDF
    with pytest.raises(ValidationError) as exc2:
        resume_extractor.extract("corrupt.pdf", b"not-a-real-pdf-header-junk")
    assert "Invalid or corrupted PDF file" in str(exc2.value)

    # 3. Too short text
    with pytest.raises(ValidationError) as exc3:
        resume_extractor.extract("short.txt", b"too short")
    assert "insufficient content" in str(exc3.value)


def test_resume_service_upload_and_replacement_flow(db_session: Session):
    """Verifies uploading an initial resume and then replacing it with an updated version."""
    user = User(
        email=f"resume_user_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hash",
        full_name="Resume Candidate",
    )
    db_session.add(user)
    db_session.flush()

    # 1. Initial upload (v1)
    file_bytes_v1 = b"Alex Developer - Version 1 Resume. Senior Python Engineer with 6 years experience."
    resume_obj, upload_res = resume_service.upload_and_process_resume(
        db=db_session,
        user=user,
        filename="resume_v1.txt",
        file_bytes=file_bytes_v1,
    )

    assert upload_res.file_name == "resume_v1.txt"
    assert "Version 1 Resume" in resume_obj.extracted_text
    initial_id = resume_obj.id

    # 2. Re-upload updated resume (v2) for same user
    file_bytes_v2 = b"Alex Developer - Version 2 Resume. Staff Python Engineer with 8 years experience."
    resume_obj_v2, upload_res_v2 = resume_service.upload_and_process_resume(
        db=db_session,
        user=user,
        filename="resume_v2.txt",
        file_bytes=file_bytes_v2,
    )

    # Must update existing record since user_id has a unique constraint
    assert resume_obj_v2.id == initial_id
    assert resume_obj_v2.file_name == "resume_v2.txt"
    assert "Version 2 Resume" in resume_obj_v2.extracted_text


def test_api_resume_lifecycle_and_user_isolation(client: TestClient, db_session: Session):
    """Tests the full API lifecycle: upload, get detail, get raw text, delete, and isolation."""
    # 1. Setup User A and User B
    def setup_user(prefix: str):
        email_addr = f"{prefix}_{uuid.uuid4().hex[:6]}@test.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email_addr, "password": "Password123!", "full_name": f"{prefix} User"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email_addr, "password": "Password123!"},
        )
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    headers_a = setup_user("user_a")
    headers_b = setup_user("user_b")

    # 2. User A: Initially has no resume
    get_404 = client.get("/api/v1/resumes/me", headers=headers_a)
    assert get_404.status_code == 404

    # 3. User A: Upload resume
    resume_text = (
        "Candidate A Resume\n"
        "Expertise in Python, FastAPI, Microservices, and Cloud Infrastructure.\n"
        "Over 7 years of production software architecture."
    )
    files = {"file": ("my_resume.txt", io.BytesIO(resume_text.encode("utf-8")), "text/plain")}
    upload_resp = client.post("/api/v1/resumes/upload", headers=headers_a, files=files)
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    assert upload_data["file_name"] == "my_resume.txt"
    assert upload_data["word_count"] > 10

    # 4. User A: Retrieve resume details
    detail_resp = client.get("/api/v1/resumes/me", headers=headers_a)
    assert detail_resp.status_code == 200
    assert "Candidate A Resume" in detail_resp.json()["extracted_text"]

    # 5. User A: Retrieve raw text
    text_resp = client.get("/api/v1/resumes/me/text", headers=headers_a)
    assert text_resp.status_code == 200
    assert text_resp.json()["file_name"] == "my_resume.txt"
    assert "Candidate A Resume" in text_resp.json()["extracted_text"]

    # 6. User B isolation: User B must NOT see User A's resume
    user_b_get = client.get("/api/v1/resumes/me", headers=headers_b)
    assert user_b_get.status_code == 404

    # 7. User A: Delete resume
    del_resp = client.delete("/api/v1/resumes/me", headers=headers_a)
    assert del_resp.status_code == 200

    # 8. User A: After deletion, querying resume returns 404
    post_del_get = client.get("/api/v1/resumes/me", headers=headers_a)
    assert post_del_get.status_code == 404
