import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from sqlalchemy import select

from app.models.email import Email
from app.models.user import User
from app.schemas.nlp import EmailCategory, EmailClassificationResult
from app.services.nlp.adapters import GeminiAdapter, OllamaAdapter, OpenAIAdapter, get_llm_adapter
from app.services.nlp.classifier import email_classifier


def test_classify_interview_invitation():
    """Verify invitation to interview is classified as INTERVIEW with high confidence."""
    subject = "Invitation to Interview: Senior Backend Engineer at Stripe"
    sender = "recruiting@stripe.com"
    body = (
        "Hi Alex, We reviewed your application and would love to invite you for a first round "
        "technical interview. Please schedule an interview with our engineering manager using "
        "the following Calendly link: https://calendly.com/stripe-recruiting/30min"
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.INTERVIEW
    assert result.confidence >= 0.85
    assert "INTERVIEW" in result.reason
    assert len(result.signals_detected) > 0


def test_classify_job_offer():
    """Verify job offer letter is classified as OFFER."""
    subject = "Offer of Employment: Lead Software Architect at Databricks"
    sender = "hr@databricks.com"
    body = (
        "Dear Alex, We are pleased to offer you the position of Lead Software Architect! "
        "Please find your official offer letter and compensation package details attached. "
        "Congratulations on your offer!"
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.OFFER
    assert result.confidence >= 0.90
    assert "OFFER" in result.reason


def test_classify_rejection():
    """Verify rejection email is classified as REJECTION."""
    subject = "Update on your application at Google"
    sender = "no-reply@google.com"
    body = (
        "Thank you for your interest in Google and for taking the time to speak with us. "
        "Unfortunately, after careful consideration, we have decided to pursue other candidates "
        "whose experience more closely aligns with our current needs. We will keep your resume "
        "on file for future opportunities."
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.REJECTION
    assert result.confidence >= 0.85
    assert "REJECTION" in result.reason


def test_classify_application_update():
    """Verify application acknowledgement is classified as APPLICATION_UPDATE."""
    subject = "Thank you for applying to Meta"
    sender = "careers@meta.com"
    body = (
        "We have received your application for the Software Engineer position. "
        "Our team is currently reviewing your candidacy and will be in touch regarding next steps."
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.APPLICATION_UPDATE
    assert result.confidence >= 0.80


def test_classify_job_alert():
    """Verify aggregated job alert is classified as JOB_ALERT."""
    subject = "15 new jobs matching 'Python Developer' in Remote"
    sender = "jobalerts-noreply@linkedin.com"
    body = (
        "Here is your daily job alert. Recommended jobs for you: Senior Python Engineer at Netflix, "
        "Backend Developer at Spotify, Data Platform Engineer at Airbnb."
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.JOB_ALERT
    assert result.confidence >= 0.80


def test_classify_direct_job_opportunity():
    """Verify recruiter outreach for an open role is classified as JOB."""
    subject = "Exciting Job Opportunity: Principal Python Engineer"
    sender = "recruiter@hiringtech.com"
    body = (
        "We are hiring a Principal Python Engineer. Requirements: 5+ years with FastAPI and PostgreSQL. "
        "Responsibilities: Design scalable cloud architectures. Apply now by replying to this email."
    )
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.JOB
    assert result.confidence >= 0.75


def test_classify_promotions_and_newsletters():
    """Verify marketing coaching is PROMOTION and newsletters are NEWSLETTER."""
    promo_subj = "Boost your career with 50% off professional resume review!"
    promo_body = "Limited time offer. Enroll today in our exclusive interview coaching webinar."
    promo_res = email_classifier.classify(subject=promo_subj, sender="promo@careerboost.io", body=promo_body)
    assert promo_res.category == EmailCategory.PROMOTION

    news_subj = "Python Weekly Newsletter - Issue #450"
    news_body = "Here are the top tech insights and weekly editorial stories in the Python ecosystem."
    news_res = email_classifier.classify(subject=news_subj, sender="editor@pythonweekly.com", body=news_body)
    assert news_res.category == EmailCategory.NEWSLETTER


def test_classify_other_unrelated():
    """Verify general personal emails or receipts fall back to OTHER."""
    subject = "Your Amazon.com order has shipped"
    sender = "shipment-tracking@amazon.com"
    body = "Your package containing USB-C Cable will arrive tomorrow by 8 PM."
    result = email_classifier.classify(subject=subject, sender=sender, body=body)
    assert result.category == EmailCategory.OTHER


def test_llm_adapter_factory():
    """Verify adapter factory instantiates appropriate provider."""
    with patch("app.core.config.settings.LLM_PROVIDER", "gemini"):
        adapter = get_llm_adapter()
        assert isinstance(adapter, GeminiAdapter)

    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        adapter = get_llm_adapter()
        assert isinstance(adapter, OllamaAdapter)

    with patch("app.core.config.settings.LLM_PROVIDER", "openai"):
        adapter = get_llm_adapter()
        assert isinstance(adapter, OpenAIAdapter)


def test_api_classify_email_and_isolation(client, db_session):
    """Verify POST /emails/{id}/classify updates database record and enforces user isolation."""
    pwd = "SecurePassword123!"
    email_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    email_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"

    client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd})
    user_a = db_session.scalar(select(User).where(User.email == email_a.lower()))
    user_b = db_session.scalar(select(User).where(User.email == email_b.lower()))

    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pwd}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pwd}).json()["access_token"]

    # Ingest unclassified email for User A
    email_record = Email(
        user_id=user_a.id,
        gmail_message_id=f"msg_interview_{uuid.uuid4().hex[:6]}",
        sender="careers@google.com",
        recipient=user_a.email,
        subject="Invitation to Interview: Software Engineer",
        body_text="We would like to invite you for a phone screen interview next week.",
        received_at=datetime.now(timezone.utc),
        category="OTHER",
        processed_status="PENDING",
    )
    db_session.add(email_record)
    db_session.commit()
    db_session.refresh(email_record)

    # 1. User B attempts to classify User A's email -> 404
    resp_b = client.post(
        f"/api/v1/emails/{email_record.id}/classify",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == status.HTTP_404_NOT_FOUND

    # 2. User A classifies own email -> 200 OK
    resp_a = client.post(
        f"/api/v1/emails/{email_record.id}/classify",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == status.HTTP_200_OK
    data = resp_a.json()
    assert data["category"] == "INTERVIEW"
    assert data["processed_status"] == "CLASSIFIED"
    assert data["classification_confidence"] is not None
    assert "INTERVIEW" in data["classification_reason"]

    # 3. Verify in database
    db_session.refresh(email_record)
    assert email_record.category == "INTERVIEW"
    assert email_record.processed_status == "CLASSIFIED"

    # 4. Batch classify endpoint
    batch_resp = client.post(
        "/api/v1/emails/classify-all",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert batch_resp.status_code == status.HTTP_200_OK
    assert "Batch classification complete" in batch_resp.json()["message"]
