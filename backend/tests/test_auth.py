"""
backend/tests/test_auth.py
─────────────────────────────────────────────────────────────
Test suites for user authentication routes — registration, login,
session validation, and input-validation edge cases.

No local ``get_auth_headers()`` — uses ``auth_headers`` fixture from
conftest.py where needed.
"""

from __future__ import annotations


def test_register_user(client) -> None:
    """Successful registration should return 201 with user data (no password hash)."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_username(client) -> None:
    """Registering a taken username should return 400 with a clear message."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"


def test_register_duplicate_email(client) -> None:
    """Registering a taken email should return 400 with a clear message."""
    client.post(
        "/api/auth/register",
        json={
            "username": "user_a",
            "email": "same@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/register",
        json={
            "username": "user_b",
            "email": "same@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_register_short_username(client) -> None:
    """A username shorter than 3 characters should be rejected by validation."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "ab",
            "email": "short@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 422  # Pydantic validation error


def test_register_short_password(client) -> None:
    """A password shorter than 6 characters should be rejected by validation."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": "12345",
        },
    )
    assert response.status_code == 422  # Pydantic validation error


def test_register_invalid_email(client) -> None:
    """An invalid email format should be rejected by Pydantic's EmailStr validator."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "validuser",
            "email": "not-an-email",
            "password": "password123",
        },
    )
    assert response.status_code == 422


def test_login_success(client) -> None:
    """Valid credentials should return a JWT access token with user data."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"


def test_login_invalid_credentials(client) -> None:
    """Invalid password should return 401 Unauthorized."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_nonexistent_user(client) -> None:
    """Attempting login with a non-existent username should return 401."""
    response = client.post(
        "/api/auth/login",
        data={"username": "ghost_user", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_me(client, auth_headers) -> None:
    """Authenticated /me endpoint should return the current user's profile.

    The ``auth_headers`` fixture generates a unique ``fixture_user_<hex>``
    username per invocation, so we assert on the prefix rather than an
    exact match to remain resilient to the uuid suffix.
    """
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"].startswith("fixture_user")
    assert "id" in data
    assert "email" in data
    assert "points" in data
    assert "level" in data


def test_get_me_unauthenticated(client) -> None:
    """Accessing /me without a token must return 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token(client) -> None:
    """Accessing /me with a malformed token must return 401."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


def test_get_me_with_expired_token(client) -> None:
    """Accessing /me with an expired token should return 401."""
    from datetime import timedelta

    from backend.app.auth import create_access_token

    expired_token = create_access_token(
        data={"sub": "fixture_user"},
        expires_delta=timedelta(seconds=-1),
    )
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
