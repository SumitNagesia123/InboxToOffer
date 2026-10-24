import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from sqlalchemy import select

from app.core.encryption import decrypt_token, encrypt_token
from app.models.oauth import OAuthCredential
from app.models.user import User
from app.services.gmail_oauth_service import gmail_oauth_service


def test_fernet_token_encryption_decryption():
    """Verify that credentials are encrypted and decrypted accurately."""
    raw_token = "ya29.a0AfH6SMD_MockAccessToken123456789"
    cipher_text = encrypt_token(raw_token)

    assert cipher_text != raw_token
    assert len(cipher_text) > len(raw_token)
    assert not cipher_text.startswith("ya29")

    decrypted = decrypt_token(cipher_text)
    assert decrypted == raw_token

    # Verify empty string handling
    assert encrypt_token("") == ""
    assert decrypt_token("") == ""


def test_oauth_state_generation_and_validation():
    """Verify state token encodes user ID and resists tampering."""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    state = gmail_oauth_service.create_oauth_state(user_id)
    assert state is not None

    # Valid validation
    assert gmail_oauth_service.verify_oauth_state(state, user_id) is True

    # Invalid user validation
    assert gmail_oauth_service.verify_oauth_state(state, other_user_id) is False

    # Tampered state
    assert gmail_oauth_service.verify_oauth_state(state + "tampered", user_id) is False


def test_gmail_connect_url_generation(client):
    """Verify /gmail/connect requires authentication and yields a Google consent URL."""
    # Unauthenticated
    unauth_resp = client.get("/api/v1/gmail/connect")
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Register & Login user
    email = f"oauth_user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pwd}).json()["access_token"]

    # Authenticated request
    resp = client.get("/api/v1/gmail/connect", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "authorization_url" in data
    assert "accounts.google.com" in data["authorization_url"]
    assert "access_type=offline" in data["authorization_url"]
    assert "scope=" in data["authorization_url"]
    assert data["state"] is not None


def test_gmail_status_unconnected(client):
    """Verify status is disconnected for a new user."""
    email = f"status_user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pwd}).json()["access_token"]

    resp = client.get("/api/v1/gmail/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["connected"] is False
    assert data["scopes"] == []


def test_gmail_oauth_callback_and_storage(client, db_session):
    """Verify OAuth callback exchange stores encrypted credentials and updates status."""
    email = f"callback_user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    user = db_session.scalar(select(User).where(User.email == email.lower()))
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pwd}).json()["access_token"]

    state = gmail_oauth_service.create_oauth_state(user.id)
    mock_code = "mock_auth_code_xyz"
    raw_access_token = "ya29.mock_access_token_value_abc"
    raw_refresh_token = "1//04_mock_refresh_token_value_def"

    # Mock Google Flow exchange
    mock_creds = MagicMock()
    mock_creds.token = raw_access_token
    mock_creds.refresh_token = raw_refresh_token
    mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_creds.scopes = gmail_oauth_service.SCOPES

    with patch("google_auth_oauthlib.flow.Flow.fetch_token") as mock_fetch:
        with patch("google_auth_oauthlib.flow.Flow.credentials", new=mock_creds):
            # POST callback
            resp = client.post(
                "/api/v1/gmail/callback",
                headers={"Authorization": f"Bearer {token}"},
                json={"code": mock_code, "state": state},
            )
            assert resp.status_code == status.HTTP_200_OK
            status_data = resp.json()
            assert status_data["connected"] is True
            assert len(status_data["scopes"]) > 0

    # Verify credentials stored in DB are ENCRYPTED, not plaintext
    db_cred = db_session.scalar(select(OAuthCredential).where(OAuthCredential.user_id == user.id))
    assert db_cred is not None
    assert db_cred.encrypted_access_token != raw_access_token
    assert db_cred.encrypted_refresh_token != raw_refresh_token
    assert decrypt_token(db_cred.encrypted_access_token) == raw_access_token
    assert decrypt_token(db_cred.encrypted_refresh_token) == raw_refresh_token

    # Verify GET /gmail/status now returns connected
    status_resp = client.get("/api/v1/gmail/status", headers={"Authorization": f"Bearer {token}"})
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["connected"] is True


def test_gmail_disconnect_and_user_isolation(client, db_session):
    """Verify disconnecting Gmail removes credentials and isolates User A from User B."""
    email_a = f"usera_oauth_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"userb_oauth_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"

    # Create User A and User B
    client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd})
    user_a = db_session.scalar(select(User).where(User.email == email_a.lower()))
    user_b = db_session.scalar(select(User).where(User.email == email_b.lower()))

    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pwd}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pwd}).json()["access_token"]

    # Connect User A's Gmail via direct service helper
    oauth_a = OAuthCredential(
        user_id=user_a.id,
        provider="google",
        encrypted_access_token=encrypt_token("access_a"),
        encrypted_refresh_token=encrypt_token("refresh_a"),
        client_id="mock_client_id",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(oauth_a)
    db_session.commit()

    # User A status is connected
    status_a = client.get("/api/v1/gmail/status", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert status_a["connected"] is True

    # User B status MUST be disconnected (tenant isolation)
    status_b = client.get("/api/v1/gmail/status", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert status_b["connected"] is False

    # Disconnect User A
    with patch("requests.post") as mock_revoke:
        mock_revoke.return_value.status_code = 200
        disc_resp = client.delete("/api/v1/gmail/disconnect", headers={"Authorization": f"Bearer {token_a}"})
        assert disc_resp.status_code == status.HTTP_200_OK
        assert disc_resp.json()["success"] is True

    # User A status is now disconnected
    status_a_after = client.get("/api/v1/gmail/status", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert status_a_after["connected"] is False

    # DB record is deleted
    assert db_session.scalar(select(OAuthCredential).where(OAuthCredential.user_id == user_a.id)) is None
