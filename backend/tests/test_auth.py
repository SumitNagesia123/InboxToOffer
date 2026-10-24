import uuid
import pytest
from fastapi import status
from sqlalchemy import select
from app.models.user import User


def test_user_registration_success(client, db_session):
    """Verify user registration returns 201 and stores a hashed password."""
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "full_name": "Alice Candidate",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == email.lower()
    assert data["full_name"] == "Alice Candidate"
    assert "id" in data
    assert "password" not in data

    # Verify password in DB is bcrypt hashed, not plaintext
    db_user = db_session.scalar(select(User).where(User.email == email.lower()))
    assert db_user is not None
    assert db_user.hashed_password != "StrongPassword123!"
    assert db_user.hashed_password.startswith("$2b$") or db_user.hashed_password.startswith("$2a$")

    # Clean up
    db_session.delete(db_user)
    db_session.commit()


def test_user_registration_duplicate_email(client, db_session):
    """Verify registration with duplicate email returns 409 Conflict."""
    email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Original User",
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == status.HTTP_201_CREATED

    # Attempt duplicate registration
    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == status.HTTP_409_CONFLICT
    data = resp2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CONFLICT"

    # Clean up
    db_user = db_session.scalar(select(User).where(User.email == email.lower()))
    if db_user:
        db_session.delete(db_user)
        db_session.commit()


def test_user_registration_validation(client):
    """Verify registration validates email format and password length."""
    # Short password (< 8 chars)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert resp.status_code == 422

    # Invalid email
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!"},
    )
    assert resp.status_code == 422


def test_user_login_success_and_token(client, db_session):
    """Verify login with valid credentials returns JWT Bearer token."""
    email = f"login_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Login Tester"},
    )
    assert reg_resp.status_code == status.HTTP_201_CREATED

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0

    # Clean up
    db_user = db_session.scalar(select(User).where(User.email == email.lower()))
    if db_user:
        db_session.delete(db_user)
        db_session.commit()


def test_user_login_invalid_credentials(client, db_session):
    """Verify login fails with wrong password or non-existent user."""
    email = f"wrong_pw_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "RealPassword123!"},
    )

    # Wrong password
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"

    # Non-existent user
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "non_existent@example.com", "password": "Password123!"},
    )
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED

    # Clean up
    db_user = db_session.scalar(select(User).where(User.email == email.lower()))
    if db_user:
        db_session.delete(db_user)
        db_session.commit()


def test_get_current_user_and_isolation(client, db_session):
    """Verify /auth/me returns current user and isolates User A from User B."""
    email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SharedSecurePassword123!"

    # Register both users
    client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd, "full_name": "User Alpha"})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd, "full_name": "User Beta"})

    # Login User A
    login_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pwd}).json()
    token_a = login_a["access_token"]

    # Login User B
    login_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pwd}).json()
    token_b = login_b["access_token"]

    # Access /auth/me with User A token
    resp_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == status.HTTP_200_OK
    assert resp_a.json()["email"] == email_a.lower()
    assert resp_a.json()["full_name"] == "User Alpha"

    # Access /auth/me with User B token
    resp_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == status.HTTP_200_OK
    assert resp_b.json()["email"] == email_b.lower()
    assert resp_b.json()["full_name"] == "User Beta"

    # Update User A profile
    update_resp = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"full_name": "User Alpha Updated"},
    )
    assert update_resp.status_code == status.HTTP_200_OK
    assert update_resp.json()["full_name"] == "User Alpha Updated"

    # Verify User B was NOT modified
    verify_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert verify_b.json()["full_name"] == "User Beta"

    # Clean up
    for em in (email_a, email_b):
        u = db_session.scalar(select(User).where(User.email == em.lower()))
        if u:
            db_session.delete(u)
    db_session.commit()


def test_auth_me_unauthenticated(client):
    """Verify /auth/me rejects unauthenticated or invalid tokens."""
    # Missing token
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Malformed token
    resp2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad_token_xyz"})
    assert resp2.status_code == status.HTTP_401_UNAUTHORIZED
