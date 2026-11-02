"""Tests for the MCP OAuth authorization server and protected /mcp endpoint.

These exercise the browser-facing half of the OAuth 2.0 Authorization Code + PKCE
flow (discovery metadata, dynamic client registration, the login -> authorize ->
token exchange, refresh, and revocation) plus the bearer-token protection on the
``/mcp`` endpoint. They rely on the seeded admin user created by the ``client``
fixture (admin@example.com / secret123).
"""

import asyncio
import base64
import hashlib
import json
import secrets
from datetime import UTC
from urllib.parse import unquote

from app.assistant.mcp_oauth import MCP_AUTH_CLAIMS, get_mcp_claims
from app.assistant.mcp_server import WRITE_TOOLS, _build_handler, iter_mcp_specs


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _new_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


REDIRECT_URI = "http://localhost/callback"


# ---------------------------------------------------------------------------
# Discovery metadata
# ---------------------------------------------------------------------------


def test_authorization_server_metadata(client):
    resp = client.get("/.well-known/oauth-authorization-server")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["issuer"].endswith("/api/v1") or "localhost" in meta["issuer"]
    assert meta["authorization_endpoint"].endswith("/oauth/authorize")
    assert meta["token_endpoint"].endswith("/oauth/token")
    assert meta["registration_endpoint"].endswith("/oauth/register")
    assert "S256" in meta["code_challenge_methods_supported"]


def test_protected_resource_metadata(client):
    resp = client.get("/.well-known/oauth-protected-resource")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["resource"].endswith("/mcp")


# ---------------------------------------------------------------------------
# Dynamic client registration
# ---------------------------------------------------------------------------


def _register_client(client):
    resp = client.post(
        "/oauth/register",
        json={
            "client_name": "Test MCP Client",
            "redirect_uris": [REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "scope": "mcp",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["client_id"]
    assert body["redirect_uris"] == [REDIRECT_URI]
    assert "code" in body["response_types"]
    return body["client_id"]


def test_dynamic_client_registration(client):
    _register_client(client)


# ---------------------------------------------------------------------------
# Full authorization-code + PKCE flow
# ---------------------------------------------------------------------------


def _register(client):
    return _register_client(client)


def _authorize_and_exchange(client, client_id):
    verifier = _new_verifier()
    challenge = _s256(verifier)

    # 1. Authorize without a session cookie -> login page (200, not a redirect).
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "xyz123",
        "scope": "mcp",
    }
    resp = client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    assert resp.status_code == 200
    assert "Sign in to authorize MCP" in resp.text

    # 2. Log in (sets the mcp_session cookie).
    login = client.post(
        "/oauth/login",
        data={"email": "admin@example.com", "password": "secret123", "next": "/oauth/authorize"},
        follow_redirects=False,
    )
    assert login.status_code == 302
    assert "mcp_session" in client.cookies

    # 3. Authorize again with the session cookie -> 302 to redirect_uri with code.
    resp2 = client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    assert resp2.status_code == 302
    location = resp2.headers["location"]
    assert location.startswith(REDIRECT_URI + "?")
    assert "code=" in location
    assert "state=xyz123" in location

    code = location.split("code=", 1)[1].split("&")[0]

    # 4. Exchange the code (+ PKCE verifier) for tokens.
    token_resp = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
        },
    )
    assert token_resp.status_code == 200
    tokens = token_resp.json()
    assert tokens["token_type"] == "Bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert "mcp" in tokens["scope"]
    return tokens


def test_authorization_code_pkce_flow(client):
    client_id = _register(client)
    tokens = _authorize_and_exchange(client, client_id)
    assert tokens["access_token"]


def test_token_exchange_rejects_bad_pkce(client):
    client_id = _register(client)
    verifier = _new_verifier()
    challenge = _s256(verifier)

    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "mcp",
    }
    client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    client.post(
        "/oauth/login",
        data={"email": "admin@example.com", "password": "secret123", "next": "/oauth/authorize"},
        follow_redirects=False,
    )
    resp2 = client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    code = resp2.headers["location"].split("code=", 1)[1].split("&")[0]

    # Wrong verifier -> invalid_grant.
    bad = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": _new_verifier(),
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
        },
    )
    assert bad.status_code == 400
    assert bad.json()["detail"] == "invalid_grant"


def test_authorize_rejects_plain_pkce(client):
    client_id = _register(client)
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "code_challenge": "abc",
        "code_challenge_method": "plain",
        "scope": "mcp",
    }
    # Unauthenticated -> login page; the plain-method rejection only applies once
    # the user is logged in, so log in first then re-check.
    client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    client.post(
        "/oauth/login",
        data={"email": "admin@example.com", "password": "secret123", "next": "/oauth/authorize"},
        follow_redirects=False,
    )
    resp2 = client.get("/oauth/authorize", params=auth_params, follow_redirects=False)
    assert resp2.status_code == 302
    assert "error=invalid_request" in resp2.headers["location"]


# ---------------------------------------------------------------------------
# Refresh + revocation
# ---------------------------------------------------------------------------


def test_refresh_token(client):
    client_id = _register(client)
    tokens = _authorize_and_exchange(client, client_id)

    refresh = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": client_id,
        },
    )
    assert refresh.status_code == 200
    body = refresh.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_revoke_token(client):
    client_id = _register(client)
    tokens = _authorize_and_exchange(client, client_id)

    revoke = client.post(
        "/oauth/revoke",
        data={"token": tokens["refresh_token"]},
    )
    assert revoke.status_code == 200

    # The revoked refresh token no longer works.
    refresh = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": client_id,
        },
    )
    assert refresh.status_code == 400


# ---------------------------------------------------------------------------
# /mcp endpoint protection
# ---------------------------------------------------------------------------


def test_mcp_requires_bearer_token(client):
    # The client fixture sets a default Authorization header, so drop it to test
    # the unauthenticated case. We hit ``/mcp/`` (the trailing-slash form) so the
    # request reaches the bearer-auth middleware rather than Starlette's
    # ``/mcp`` -> ``/mcp/`` redirect.
    prior = client.headers.pop("Authorization", None)
    try:
        # No token at all -> 401.
        resp = client.get("/mcp/", follow_redirects=False)
        assert resp.status_code == 401
    finally:
        if prior is not None:
            client.headers["Authorization"] = prior

    # Garbage token -> 401.
    resp2 = client.get("/mcp/", headers={"Authorization": "Bearer not-a-real-token"}, follow_redirects=False)
    assert resp2.status_code == 401


def test_mcp_accepts_valid_token(client):
    # The full bearer-middleware "accept" path can't be exercised through the
    # streamable-HTTP transport under TestClient (its session manager requires a
    # running task group). Instead verify the verifier the middleware delegates
    # to accepts a real app JWT and rejects garbage — the 401 cases above prove
    # the middleware itself runs and rejects invalid tokens. The ``client``
    # fixture seeds the admin user (id 1) the token refers to.
    from app.assistant.mcp_oauth import StockwireTokenVerifier
    from app.domain.auth.security import create_access_token

    token = create_access_token(1, "admin@example.com", "admin")
    result = asyncio.run(StockwireTokenVerifier().verify_token(token))
    assert result is not None
    assert result.subject == "1"
    assert "mcp" in result.scopes
    # The original JWT claims are carried on the AccessToken for the tool
    # handlers to gate on (admin-only write tools check the role).
    assert result.claims["role"] == "admin"

    bad = asyncio.run(StockwireTokenVerifier().verify_token("not-a-real-token"))
    assert bad is None


def test_mcp_verifier_rejects_disabled_user(test_engine):
    from datetime import datetime

    from sqlalchemy.orm import sessionmaker

    from app.assistant.mcp_oauth import StockwireTokenVerifier
    from app.domain.auth.models import User
    from app.domain.auth.security import create_access_token

    # Insert a disabled user directly into the test engine.
    TestingSession = sessionmaker(bind=test_engine)
    with TestingSession() as db:
        db.add(
            User(
                id=4242,
                email="disabled@example.com",
                password_hash="x",
                full_name="Disabled",
                role="admin",
                is_active=False,
                auth_source="local",
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

    token = create_access_token(4242, "disabled@example.com", "admin")
    result = asyncio.run(StockwireTokenVerifier().verify_token(token))
    # A disabled user must be rejected even with a structurally valid token.
    assert result is None


# ---------------------------------------------------------------------------
# Admin gate on write tools (security)
# ---------------------------------------------------------------------------


def _dummy_kwargs(spec):
    """Build dummy keyword args for a handler from its declared parameters.

    The admin gate runs before the arguments are used, so exact values do not
    matter here.
    """
    props = spec["parameters"].get("properties", {})
    required = set(spec["parameters"].get("required", []))
    kwargs = {}
    for name, schema in props.items():
        t = schema.get("type", "string")
        if t == "integer":
            kwargs[name] = 1
        elif t == "number":
            kwargs[name] = 1.0
        elif t == "boolean":
            kwargs[name] = True
        elif t == "array":
            kwargs[name] = []
        elif t == "object":
            kwargs[name] = {}
        else:
            kwargs[name] = "x"
    # Supply only required args; optional ones keep their defaults.
    return {k: v for k, v in kwargs.items() if k in required}


def test_write_tools_rejected_for_non_admin(test_engine):
    spec = next(s for s in iter_mcp_specs() if s["name"] == "update_product_manufacturer")
    handler = _build_handler(spec)
    token = MCP_AUTH_CLAIMS.set({"sub": "2", "role": "user", "scopes": ["mcp"]})
    try:
        assert get_mcp_claims()["role"] == "user"
        result = json.loads(handler(**_dummy_kwargs(spec)))
        assert "Admin privileges required" in result.get("error", "")
    finally:
        MCP_AUTH_CLAIMS.reset(token)


def test_write_tools_allowed_for_admin(test_engine):
    spec = next(s for s in iter_mcp_specs() if s["name"] == "update_product_manufacturer")
    handler = _build_handler(spec)
    token = MCP_AUTH_CLAIMS.set({"sub": "1", "role": "admin", "scopes": ["mcp"]})
    try:
        assert get_mcp_claims()["role"] == "admin"
        # The gate passes; the handler proceeds (it will open a DB session and may
        # return a real result or a DB error, but it must not be the admin error).
        result = json.loads(handler(**_dummy_kwargs(spec)))
        assert "Admin privileges required" not in result.get("error", "")
    finally:
        MCP_AUTH_CLAIMS.reset(token)


def test_write_tools_set_is_non_empty():
    assert WRITE_TOOLS
    assert "update_product_manufacturer" in WRITE_TOOLS


# ---------------------------------------------------------------------------
# SSO (OIDC / SAML) bridge into /oauth/login
# ---------------------------------------------------------------------------


def _enable_sso_settings(monkeypatch, *, oidc: bool = True, saml: bool = False):
    """Turn on SSO in the test settings and register dummy providers."""
    from app.config import settings

    monkeypatch.setattr(settings, "sso_enabled", True, raising=False)
    if oidc:
        monkeypatch.setattr(
            settings,
            "oidc_providers",
            json.dumps(
                {
                    "testoidc": {
                        "display_name": "Test OIDC",
                        "client_id": "cid",
                        "client_secret": "secret",
                        "authorization_endpoint": "https://idp.example/authorize",
                        "token_endpoint": "https://idp.example/token",
                        "jwks_uri": "https://idp.example/jwks",
                        "scopes": "openid email",
                        "enabled": True,
                    }
                }
            ),
            raising=False,
        )
    if saml:
        monkeypatch.setattr(
            settings,
            "saml_providers",
            json.dumps(
                {
                    "testsaml": {
                        "display_name": "Test SAML",
                        "idp_sso_url": "https://idp.example/saml/login",
                        "idp_x509_cert": "cert",
                        "sp_entity_id": "sp",
                        "acs_url": "https://app.example/oauth/sso/saml/callback",
                        "enabled": True,
                    }
                }
            ),
            raising=False,
        )


def test_login_page_shows_sso_buttons_when_enabled(client, monkeypatch):
    _enable_sso_settings(monkeypatch, oidc=True, saml=True)
    resp = client.get("/oauth/login", follow_redirects=False)
    assert resp.status_code == 200
    assert "Continue with Test OIDC" in resp.text
    assert "Continue with Test SAML" in resp.text
    # The OIDC button links to the MCP SSO start endpoint.
    assert "/oauth/sso/oidc/start/testoidc" in resp.text


def test_login_page_hides_sso_buttons_when_disabled(client, monkeypatch):
    # Default test settings have SSO disabled.
    from app.config import settings

    monkeypatch.setattr(settings, "sso_enabled", False, raising=False)
    resp = client.get("/oauth/login", follow_redirects=False)
    assert resp.status_code == 200
    assert "Continue with" not in resp.text


def test_oidc_start_redirects_to_idp(client, monkeypatch):
    _enable_sso_settings(monkeypatch, oidc=True)
    resp = client.get(
        "/oauth/sso/oidc/start/testoidc",
        params={"next": "/oauth/authorize"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://idp.example/authorize")
    # The callback URL (with provider + next) is the OIDC redirect_uri. It is
    # URL-encoded inside the query string.
    assert "/oauth/sso/oidc/callback" in unquote(location)
    # State cookie is bound to the browser session.
    assert "oidc_state" in client.cookies


def test_oidc_start_404_when_sso_disabled(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "sso_enabled", False, raising=False)
    resp = client.get(
        "/oauth/sso/oidc/start/testoidc",
        params={"next": "/oauth/authorize"},
        follow_redirects=False,
    )
    assert resp.status_code == 404


def test_oidc_callback_sets_mcp_session_cookie(client, monkeypatch):
    _enable_sso_settings(monkeypatch, oidc=True)
    # The OIDC token exchange, identity mapping and user upsert are external /
    # network calls; mock them. Only the cookie issuance + redirect are under test.
    from app.assistant import mcp_oauth_router as router_mod
    from app.domain.auth.models import User

    monkeypatch.setattr(router_mod, "verify_oidc_state", lambda provided, expected: True)
    monkeypatch.setattr(
        router_mod, "exchange_oidc_code", lambda provider, code, uri: {"sub": "s", "email": "sso@example.com"}
    )
    monkeypatch.setattr(
        router_mod,
        "claims_to_identity",
        lambda provider, claims: {
            "subject": "s",
            "email": "sso@example.com",
            "full_name": "SSO User",
            "groups": [],
        },
    )
    monkeypatch.setattr(
        router_mod,
        "upsert_external_user",
        lambda db, **kwargs: User(
            id=1, email="sso@example.com", role="admin", is_active=True, full_name="SSO User"
        ),
    )

    # Simulate the IdP redirect back with the oidc_state cookie set by /start.
    client.cookies.set("oidc_state", "abc")
    resp = client.get(
        "/oauth/sso/oidc/callback",
        params={
            "provider": "testoidc",
            "code": "c",
            "state": "abc",
            "next": "/oauth/authorize",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("/oauth/authorize")
    assert "mcp_session" in client.cookies


def test_saml_start_redirects_to_idp(client, monkeypatch):
    _enable_sso_settings(monkeypatch, saml=True)
    resp = client.get(
        "/oauth/sso/saml/start/testsaml",
        params={"next": "/oauth/authorize"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://idp.example/saml/login")
    # RelayState carries the provider + the bounce-back URL.
    assert "RelayState=" in location
