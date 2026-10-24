import base64
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from sqlalchemy import select

from app.core.encryption import encrypt_token
from app.models.email import Email
from app.models.oauth import OAuthCredential
from app.models.user import User
from app.services.email.parser import email_parser
from app.services.email.source_detector import source_detector


def test_html_cleaning_and_link_normalization():
    """Verify HTML cleaning strips boilerplate, scripts, and tracking parameters."""
    raw_html = """
    <html>
        <head><title>Job Alert</title><style>.test { color: red; }</style></head>
        <body>
            <h1>Senior Python Engineer at Acmo Corp</h1>
            <p>We are looking for a backend engineer with 3+ years of experience in FastAPI and PostgreSQL.</p>
            <p><a href="https://jobs.example.com/view/1234?utm_source=linkedin&utm_medium=email&utm_campaign=daily_digest&ref=newsletter">Apply on Company Site</a></p>
            <footer>
                <p>You are receiving this email because you subscribed to Job Alerts.</p>
                <p><a href="https://example.com/unsubscribe">Click here to unsubscribe</a></p>
            </footer>
        </body>
    </html>
    """
    cleaned_text, links = email_parser.clean_html(raw_html)

    # Content checks
    assert "Senior Python Engineer at Acmo Corp" in cleaned_text
    assert "FastAPI and PostgreSQL" in cleaned_text
    assert "style {" not in cleaned_text

    # Unsubscribe boilerplate stripped
    assert "You are receiving this email because" not in cleaned_text
    assert "Click here to unsubscribe" not in cleaned_text

    # URL tracking params stripped
    assert len(links) >= 1
    assert "https://jobs.example.com/view/1234" in links[0]
    assert "utm_source" not in links[0]
    assert "utm_medium" not in links[0]
    assert "ref=" not in links[0]


def test_platform_source_detection():
    """Verify source detector correctly identifies platforms from senders and links."""
    assert source_detector.detect_source(sender="jobs-noreply@linkedin.com") == "LinkedIn"
    assert source_detector.detect_source(sender="alert@indeed.com") == "Indeed"
    assert source_detector.detect_source(sender="jobseeker@naukri.com") == "Naukri"
    assert source_detector.detect_source(sender="digest@internshala.com") == "Internshala"
    assert source_detector.detect_source(sender="talent@wellfound.com") == "Wellfound"
    assert source_detector.detect_source(sender="noreply@glassdoor.com") == "Glassdoor"
    assert source_detector.detect_source(sender="notifications@cutshort.io") == "Cutshort"
    assert source_detector.detect_source(sender="careers@stripe.com") == "Company career page"
    assert source_detector.detect_source(sender="info@random.org", subject="Weekly Tech Newsletter") == "Email newsletter"
    assert source_detector.detect_source(sender="unknown@domain.xyz") == "Other"

    # URL based detection
    assert source_detector.detect_source(sender="unknown@domain.xyz", urls=["https://www.linkedin.com/jobs/view/100"]) == "LinkedIn"


def test_mime_multipart_parsing():
    """Verify Gmail API payload MIME parsing."""
    html_content = "<p>New opportunity at Acme: <b>DevOps Engineer</b></p>"
    b64_html = base64.urlsafe_b64encode(html_content.encode("utf-8")).decode("utf-8")

    fake_gmail_msg = {
        "id": "gmail_msg_101",
        "threadId": "thread_101",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "New DevOps Job Opening"},
                {"name": "From", "value": "recruiter@acme.com"},
                {"name": "To", "value": "candidate@example.com"},
                {"name": "Date", "value": "Thu, 24 Sep 2026 12:00:00 +0000"},
            ],
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": b64_html},
                }
            ],
        },
    }

    parsed = email_parser.parse_gmail_message(fake_gmail_msg)
    assert parsed.message_id == "gmail_msg_101"
    assert parsed.subject == "New DevOps Job Opening"
    assert parsed.sender == "recruiter@acme.com"
    assert "DevOps Engineer" in parsed.cleaned_text


def test_gmail_sync_flow_and_api(client, db_session):
    """Verify end-to-end sync operation with mocked Gmail API service."""
    # Register and login user
    email = f"sync_test_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    user = db_session.scalar(select(User).where(User.email == email.lower()))
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pwd}).json()["access_token"]

    # Add OAuth credentials for user
    oauth = OAuthCredential(
        user_id=user.id,
        provider="google",
        encrypted_access_token=encrypt_token("mock_access"),
        encrypted_refresh_token=encrypt_token("mock_refresh"),
        client_id="mock_client_id",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(oauth)
    db_session.commit()

    # Mock Gmail API client responses
    mock_messages_list = {
        "messages": [
            {"id": "msg_001", "threadId": "t_001"},
            {"id": "msg_002", "threadId": "t_002"},
        ]
    }

    def make_fake_msg(msg_id, subject):
        html_body = f"<h2>{subject}</h2><p>Job details for {subject}.</p>"
        b64 = base64.urlsafe_b64encode(html_body.encode("utf-8")).decode("utf-8")
        return {
            "id": msg_id,
            "threadId": f"thread_{msg_id}",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": subject},
                    {"name": "From", "value": "jobs@linkedin.com"},
                    {"name": "To", "value": user.email},
                    {"name": "Date", "value": "Thu, 24 Sep 2026 14:00:00 +0000"},
                ],
                "parts": [{"mimeType": "text/html", "body": {"data": b64}}],
            },
        }

    mock_messages = MagicMock()
    mock_messages.list.return_value.execute.return_value = mock_messages_list

    def get_side_effect(userId, id, format):
        req_mock = MagicMock()
        title = "Lead Python Architect" if id == "msg_001" else "Fullstack React Developer"
        req_mock.execute.return_value = make_fake_msg(id, title)
        return req_mock

    mock_messages.get.side_effect = get_side_effect

    mock_users = MagicMock()
    mock_users.messages.return_value = mock_messages

    mock_gmail_service = MagicMock()
    mock_gmail_service.users.return_value = mock_users

    with patch("app.services.email.ingestion_service.build", return_value=mock_gmail_service):
        with patch("app.services.gmail_oauth_service.gmail_oauth_service.get_valid_credentials", return_value=MagicMock()):
            # 1. Trigger sync
            sync_resp = client.post("/api/v1/gmail/sync", headers={"Authorization": f"Bearer {token}"})
            assert sync_resp.status_code == status.HTTP_200_OK
            sync_data = sync_resp.json()
            assert sync_data["total_fetched"] == 2
            assert sync_data["new_emails_stored"] == 2
            assert sync_data["duplicates_skipped"] == 0

            # 2. Trigger sync again (duplicate detection)
            sync_resp2 = client.post("/api/v1/gmail/sync", headers={"Authorization": f"Bearer {token}"})
            assert sync_resp2.status_code == status.HTTP_200_OK
            assert sync_resp2.json()["new_emails_stored"] == 0
            assert sync_resp2.json()["duplicates_skipped"] == 2

    # 3. List emails via /api/v1/emails
    list_resp = client.get("/api/v1/emails", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == status.HTTP_200_OK
    list_data = list_resp.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2
    assert any("Lead Python Architect" in it["subject"] for it in list_data["items"])

    # 4. Search email
    search_resp = client.get("/api/v1/emails?search=Architect", headers={"Authorization": f"Bearer {token}"})
    assert search_resp.status_code == status.HTTP_200_OK
    assert search_resp.json()["total"] == 1

    # 5. Fetch single email detail
    email_id = list_data["items"][0]["id"]
    detail_resp = client.get(f"/api/v1/emails/{email_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == status.HTTP_200_OK
    detail_data = detail_resp.json()
    assert detail_data["body_text"] is not None
    assert detail_data["sender"] == "jobs@linkedin.com"


def test_email_user_isolation(client, db_session):
    """Verify User A cannot access User B's emails."""
    pwd = "SecurePassword123!"
    email_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    email_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"

    client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd})
    user_a = db_session.scalar(select(User).where(User.email == email_a.lower()))
    user_b = db_session.scalar(select(User).where(User.email == email_b.lower()))

    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pwd}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pwd}).json()["access_token"]

    # Insert an email for User A
    email_record = Email(
        user_id=user_a.id,
        gmail_message_id=f"msg_alice_{uuid.uuid4().hex[:6]}",
        sender="confidential@apple.com",
        recipient=user_a.email,
        subject="Confidential Offer from Apple",
        body_text="Confidential job offer details.",
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(email_record)
    db_session.commit()
    db_session.refresh(email_record)

    # User A can read it
    resp_a = client.get(f"/api/v1/emails/{email_record.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == status.HTTP_200_OK

    # User B cannot read it (returns 404 Not Found)
    resp_b = client.get(f"/api/v1/emails/{email_record.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == status.HTTP_404_NOT_FOUND

    # User B's email list does not contain User A's email
    list_b = client.get("/api/v1/emails", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert list_b["total"] == 0
