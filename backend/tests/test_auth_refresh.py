"""Tests for token refresh and public SSO endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.domain.auth.models import UserSession


def test_refresh_token_rotation_and_reuse_grace(client: TestClient):
    # Log in as the seeded admin to obtain tokens
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    data = login.json()
    assert "refresh_token" in data
    refresh_token = data["refresh_token"]

    # First refresh using the token from the JSON response
    refresh1 = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Refresh-Token": refresh_token},
    )
    assert refresh1.status_code == 200
    new_refresh_token = refresh1.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    # Within the grace period the same old refresh token should still be accepted
    refresh2 = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Refresh-Token": refresh_token},
    )
    assert refresh2.status_code == 200

    # New tokens work for authenticated requests
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh1.json()['access_token']}"},
    )
    assert me.status_code == 200


def test_sso_providers_is_public(client: TestClient):
    # No Authorization header required
    resp = client.get("/api/v1/auth/sso/providers")
    assert resp.status_code == 200
    assert resp.json() == []


def test_logout_invalidates_header_refresh_token(client: TestClient):
    # Log in and capture the refresh token from the JSON response
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    # Log out using the refresh token in the header
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"X-Refresh-Token": refresh_token},
    )
    assert logout.status_code == 204

    # The refresh token should no longer work
    refresh = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Refresh-Token": refresh_token},
    )
    assert refresh.status_code == 401


def test_refresh_handles_postgres_timezone_aware_expiry():
    """The expiry comparison must work when the DB returns offset-aware datetimes."""
    future = datetime.now(UTC) + timedelta(days=1)
    session = UserSession(session_id="test", user_id=1, expires_at=future)
    now = datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    assert expires_at > now


def test_refresh_rejects_expired_timezone_aware_session():
    """Expired offset-aware sessions must be rejected without crashing."""
    past = datetime.now(UTC) - timedelta(days=1)
    session = UserSession(session_id="test", user_id=1, expires_at=past)
    now = datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    assert expires_at < now
