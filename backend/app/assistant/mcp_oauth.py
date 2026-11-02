"""
OAuth 2.0 (Authorization Code + PKCE) plumbing for the MCP server.

This module is the bridge between the MCP protocol and Stockwire's existing
user store:

* :class:`StockwireTokenVerifier` validates the access tokens the MCP server
  issues (the app's own JWT format) and records the decoded claims in a
  :data:`MCP_AUTH_CLAIMS` contextvar so the tool handlers can enforce that only
  admins may call the write tools.
* The helper functions manage OAuth clients, single-use authorization codes, and
  refresh tokens, all backed by the database models in
  :mod:`app.assistant.mcp_oauth_models`.

The HTTP routes that drive the browser login and token exchange live in
``app.assistant.mcp_oauth_router``; this module is the protocol/DB layer.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.mcp_oauth_models import McpAuthCode, McpOAuthClient, McpRefreshToken
from app.config import settings
from app.domain.auth.models import User
from app.domain.auth.security import decode_token

# The single OAuth scope exposed to MCP clients.
SCOPE = "mcp"

# Decoded JWT claims for the currently authenticated MCP request. Populated by
# :class:`StockwireTokenVerifier.verify_token` and read by the tool handlers to
# gate admin-only tools. ``None`` means "no authenticated principal".
MCP_AUTH_CLAIMS: ContextVar[dict[str, Any] | None] = ContextVar("mcp_auth_claims", default=None)


def get_mcp_claims() -> dict[str, Any] | None:
    """Return the claims of the currently authenticated MCP request, if any."""
    return MCP_AUTH_CLAIMS.get()


def pkce_challenge(verifier: str) -> str:
    """Compute the S256 PKCE code challenge for a code verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# OAuth clients
# ---------------------------------------------------------------------------


def register_oauth_client(
    db: Session,
    *,
    client_name: str,
    redirect_uris: list[str],
    token_endpoint_auth_method: str = "none",
    scope: str = SCOPE,
) -> McpOAuthClient:
    client = McpOAuthClient(
        client_id=secrets.token_urlsafe(24),
        client_name=client_name,
        redirect_uris="\n".join(redirect_uris),
        token_endpoint_auth_method=token_endpoint_auth_method,
        scope=scope,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_oauth_client(db: Session, client_id: str) -> McpOAuthClient | None:
    return db.scalar(select(McpOAuthClient).where(McpOAuthClient.client_id == client_id))


# ---------------------------------------------------------------------------
# Authorization codes (single use, PKCE bound, short lived)
# ---------------------------------------------------------------------------


def create_auth_code(
    db: Session,
    *,
    client_id: str,
    user_id: int,
    code_challenge: str,
    redirect_uri: str,
    scopes: list[str],
) -> str:
    code = secrets.token_urlsafe(32)
    record = McpAuthCode(
        code=code,
        client_id=client_id,
        user_id=user_id,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
        scopes=" ".join(scopes),
        expires_at=_utcnow() + timedelta(minutes=5),
    )
    db.add(record)
    db.commit()
    return code


def _as_aware(dt: datetime) -> datetime:
    """Coerce a stored datetime to an aware UTC value.

    SQLite's driver returns naive datetimes even for ``DateTime(timezone=True)``
    columns, while Postgres returns aware ones. Comparing a naive value against
    the aware ``_utcnow()`` would raise, so normalize here.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def consume_auth_code(db: Session, code: str, client_id: str) -> McpAuthCode | None:
    record = db.scalar(
        select(McpAuthCode).where(McpAuthCode.code == code, McpAuthCode.client_id == client_id)
    )
    if record is None or record.used or _as_aware(record.expires_at) < _utcnow():
        return None
    record.used = True
    db.commit()
    return record


# ---------------------------------------------------------------------------
# Refresh tokens (stored hashed; revocable)
# ---------------------------------------------------------------------------


def create_refresh_token(
    db: Session, *, client_id: str, user_id: int, scopes: list[str]
) -> str:
    raw = secrets.token_urlsafe(48)
    record = McpRefreshToken(
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        client_id=client_id,
        user_id=user_id,
        scopes=" ".join(scopes),
        expires_at=_utcnow() + timedelta(days=30),
    )
    db.add(record)
    db.commit()
    return raw


def consume_refresh_token(db: Session, raw: str) -> McpRefreshToken | None:
    record = db.scalar(
        select(McpRefreshToken).where(
            McpRefreshToken.token_hash == hashlib.sha256(raw.encode()).hexdigest()
        )
    )
    if record is None or record.revoked or _as_aware(record.expires_at) < _utcnow():
        return None
    record.revoked = True
    db.commit()
    return record


def revoke_refresh_token(db: Session, raw: str) -> bool:
    return consume_refresh_token(db, raw) is not None


# ---------------------------------------------------------------------------
# Token verifier (protects the /mcp endpoint)
# ---------------------------------------------------------------------------


class StockwireTokenVerifier(TokenVerifier):
    """Validate MCP access tokens (the app's JWT) for the /mcp endpoint.

    The token is the Stockwire JWT produced by
    :func:`app.domain.auth.security.create_access_token`. On success the decoded
    claims are stored in :data:`MCP_AUTH_CLAIMS` for the request lifetime so the
    tool handlers can enforce role-based access (e.g. admin-only writes).
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            # Any malformed / expired / non-JWT value is simply an invalid token.
            return None

        sub = payload.get("sub")
        if sub is None or not str(sub).isdigit():
            return None

        # Reject tokens for disabled users even if still within their validity
        # window, so deactivated accounts lose MCP access promptly.
        # Import lazily: the test harness rebinds ``app.db.session.SessionLocal``
        # to an in-memory engine, and a module-level import would capture the old
        # (production) binding.
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            user = db.get(User, int(sub))
        finally:
            db.close()
        if user is None or not user.is_active:
            return None

        claims = {
            "sub": str(sub),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "scopes": payload.get("scopes") or [SCOPE],
        }
        MCP_AUTH_CLAIMS.set(claims)
        return AccessToken(
            token=token,
            subject=str(sub),
            scopes=claims["scopes"],
            expires_at=int(payload.get("exp", 0)),
            # The access token is the app's own JWT (not tied to a specific OAuth
            # client), so use a stable placeholder for the required client_id.
            client_id="stockwire",
            resource=None,
            claims=payload,
        )


def mcp_issuer_url() -> str:
    """Absolute base URL the MCP/OAuth endpoints are served from."""
    raw = (getattr(settings, "mcp_issuer_url", "") or "").strip()
    if not raw:
        raw = settings.effective_api_base_url
    return raw.rstrip("/")


def mcp_authorization_server_metadata() -> dict[str, Any]:
    issuer = mcp_issuer_url()
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "scopes_supported": [SCOPE],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
        "code_challenge_methods_supported": ["S256"],
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": ["none"],
        "service_documentation": f"{issuer}/docs",
    }


def mcp_protected_resource_metadata() -> dict[str, Any]:
    issuer = mcp_issuer_url()
    return {
        "resource": f"{issuer}/mcp",
        "authorization_servers": [issuer],
        "scopes_supported": [SCOPE],
    }
