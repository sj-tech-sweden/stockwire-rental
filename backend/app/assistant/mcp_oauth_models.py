"""
Database models for the MCP OAuth authorization server.

These back the OAuth 2.0 flow the MCP server uses to authenticate outside agents
against the existing Stockwire user store:

* ``McpOAuthClient``  – registered MCP clients (dynamic client registration).
* ``McpAuthCode``    – short-lived, single-use authorization codes (PKCE bound).
* ``McpRefreshToken``– refresh tokens (revocable, stored hashed).

Access tokens themselves are stateless JWTs (the app's existing token format), so
they are not stored here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class McpOAuthClient(Base):
    __tablename__ = "mcp_oauth_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # Confidential clients store a hashed secret; public clients (PKCE) leave this null.
    client_secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_uris: Mapped[str] = mapped_column(Text, nullable=False)  # newline-separated
    token_endpoint_auth_method: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    scope: Mapped[str] = mapped_column(String(255), default="mcp", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class McpAuthCode(Base):
    __tablename__ = "mcp_oauth_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(128), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(String(255), default="mcp", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class McpRefreshToken(Base):
    __tablename__ = "mcp_oauth_refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stored as a SHA-256 digest of the raw refresh token (raw is never persisted).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    scopes: Mapped[str] = mapped_column(String(255), default="mcp", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
