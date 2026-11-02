"""
HTTP routes for the MCP OAuth 2.0 authorization server.

These run *inside* the Stockwire FastAPI app (not the MCP sub-app), so they
reuse the same process, database, CORS, and security as the rest of the API.
They implement the browser-facing half of the MCP OAuth flow:

* ``/.well-known/oauth-authorization-server`` / ``/.well-known/oauth-protected-resource``
  – discovery metadata clients use to "add" the server automatically.
* ``/oauth/register`` – dynamic client registration (public + confidential).
* ``/oauth/authorize`` – authenticates the user (via a backend login page that
  issues a session cookie) and returns an authorization code.
* ``/oauth/token`` – exchanges the code (+ PKCE verifier) for an access token, or
  refreshes an access token.
* ``/oauth/login`` – minimal backend login page for the authorize step.
* ``/oauth/revoke`` – token revocation.

The MCP *protocol* endpoint itself (``/mcp``) is mounted separately from
``app.assistant.mcp_server`` and is protected by ``StockwireTokenVerifier``.
"""

from __future__ import annotations

import base64
import html
import json
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.mcp_oauth import (
    SCOPE,
    consume_auth_code,
    consume_refresh_token,
    create_auth_code,
    create_refresh_token,
    get_oauth_client,
    mcp_authorization_server_metadata,
    mcp_issuer_url,
    mcp_protected_resource_metadata,
    pkce_challenge,
    register_oauth_client,
    revoke_refresh_token,
)
from app.assistant.mcp_oauth_models import McpOAuthClient
from app.db.session import get_db
from app.domain.auth.models import User
from app.domain.auth.schemas import SSOProviderSummary
from app.domain.auth.security import create_access_token, decode_token, verify_password
from app.domain.auth.sso import (
    build_oidc_authorize_url,
    claims_to_identity,
    exchange_oidc_code,
    get_oidc_provider,
    get_runtime_sso_config,
    get_saml_provider,
    list_enabled_providers,
    parse_saml_response,
    upsert_external_user,
    verify_oidc_state,
)

router = APIRouter()

SESSION_COOKIE = "mcp_session"
SESSION_MAX_AGE = 900  # 15 minutes — covers the interactive login -> authorize step


# ---------------------------------------------------------------------------
# Discovery metadata
# ---------------------------------------------------------------------------


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata() -> JSONResponse:
    return JSONResponse(mcp_authorization_server_metadata())


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata() -> JSONResponse:
    return JSONResponse(mcp_protected_resource_metadata())


# ---------------------------------------------------------------------------
# Dynamic client registration (RFC 7591)
# ---------------------------------------------------------------------------


@router.post("/oauth/register")
async def oauth_register(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    # Accept both JSON and form bodies.
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    client_name = str(body.get("client_name") or body.get("client_uri") or "MCP Client")
    redirect_uris = body.get("redirect_uris") or []
    if isinstance(redirect_uris, str):
        redirect_uris = [u.strip() for u in redirect_uris.replace("\r", "\n").split("\n") if u.strip()]
    if not redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uris are required")

    auth_method = str(body.get("token_endpoint_auth_method") or "none")
    scope = str(body.get("scope") or SCOPE)

    client = register_oauth_client(
        db,
        client_name=client_name,
        redirect_uris=redirect_uris,
        token_endpoint_auth_method=auth_method,
        scope=scope,
    )

    response = {
        "client_id": client.client_id,
        "client_name": client.client_name,
        "redirect_uris": redirect_uris,
        "token_endpoint_auth_method": auth_method,
        "scope": scope,
        "response_types": ["code"],
        "grant_types": ["authorization_code", "refresh_token"],
    }
    return JSONResponse(response, status_code=201)


# ---------------------------------------------------------------------------
# Authorization endpoint (Authorization Code + PKCE)
# ---------------------------------------------------------------------------


def _validate_redirect_uri(client: McpOAuthClient, redirect_uri: str | None) -> str | None:
    """Return a registered redirect URI that the client is allowed to use.

    The returned value is taken from the server-side ``client.redirect_uris``
    (not the request value) so it is never attacker-controlled beyond an exact
    allow-list match. Only well-formed http(s) or relative-path URIs are
    accepted, which prevents open redirects and breaks any taint from the request.
    """
    uris = [u.strip() for u in client.redirect_uris.split("\n") if u.strip()]
    if not uris:
        return None
    if not redirect_uri:
        return uris[0]
    for registered in uris:
        if registered == redirect_uri:
            parsed = urlparse(registered)
            if parsed.scheme == "":
                # Relative path — safe as long as it is same-origin.
                if registered.startswith("/"):
                    return registered
                return None
            if parsed.scheme in ("http", "https") and "@" not in (parsed.netloc or ""):
                return registered
            return None
    return None


def _safe_next(next_url: str | None) -> str:
    """Only allow same-origin (host-less) redirects to /oauth/authorize.

    The result is rebuilt from the parsed path + query so it can never carry a
    scheme or authority (which would make it an off-site redirect), satisfying
    open-redirect checks and the URL-redirection scanner.
    """
    default = "/oauth/authorize"
    if not next_url:
        return default

    parsed = urlparse(next_url.replace("\\", "/"))

    # Reject anything that is not a bare same-origin relative path.
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return default
    if not parsed.path.startswith("/oauth/authorize"):
        return default

    # Rebuild from trusted components only (no scheme, netloc or fragment).
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


@router.api_route("/oauth/authorize", methods=["GET", "POST"])
async def oauth_authorize(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    params = dict(request.query_params) if request.method == "GET" else dict(await request.form())

    client_id = params.get("client_id", "")
    redirect_uri_param = params.get("redirect_uri")
    code_challenge = params.get("code_challenge", "")
    state = params.get("state")
    scope = params.get("scope") or SCOPE

    client = get_oauth_client(db, client_id) if client_id else None
    if client is None:
        raise HTTPException(status_code=400, detail="Unknown client_id")

    redirect_uri = _validate_redirect_uri(client, redirect_uri_param)
    if redirect_uri is None:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    if not code_challenge:
        return _authorize_error(redirect_uri, state, "invalid_request", "code_challenge (S256) is required")

    # Only the S256 PKCE method is accepted; "plain" is forbidden (it would
    # transmit the verifier in a recoverable form).
    challenge_method = params.get("code_challenge_method", "S256")
    if challenge_method != "S256":
        return _authorize_error(redirect_uri, state, "invalid_request", "only S256 PKCE is supported")

    # Authenticate the user via the session cookie set by /oauth/login.
    session_token = request.cookies.get(SESSION_COOKIE)
    user_id: int | None = None
    if session_token:
        try:
            payload = decode_token(session_token)
            uid = int(payload["sub"]) if str(payload.get("sub", "")).isdigit() else None
            if uid is not None:
                user = db.get(User, uid)
                if user is not None and user.is_active:
                    user_id = uid
        except jwt.PyJWTError:
            # Malformed / expired session cookie — treat as unauthenticated.
            user_id = None

    if user_id is None:
        # Send the user to the login page; return here afterwards.
        authorize_url = f"/oauth/authorize?{urlencode(params)}"
        return _login_page(next_url=authorize_url, error=None, db=db)

    code = create_auth_code(
        db,
        client_id=client.client_id,
        user_id=user_id,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
        scopes=[s.strip() for s in scope.split() if s.strip()] or [SCOPE],
    )

    result = {"code": code}
    if state:
        result["state"] = state
    return _redirect(redirect_uri, result)


def _redirect(redirect_uri: str, params: dict) -> RedirectResponse:
    return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}", status_code=302)


def _authorize_error(redirect_uri: str, state: str | None, error: str, description: str) -> RedirectResponse:
    params = {"error": error, "error_description": description}
    if state:
        params["state"] = state
    return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}", status_code=302)


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------


@router.post("/oauth/token")
async def oauth_token(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)

    grant_type = body.get("grant_type")

    if grant_type == "authorization_code":
        return await _token_from_code(body, db)
    if grant_type == "refresh_token":
        return await _token_from_refresh(body, db)
    raise HTTPException(status_code=400, detail="unsupported_grant_type")


async def _token_from_code(body: dict, db: Session) -> JSONResponse:
    code = body.get("code", "")
    code_verifier = body.get("code_verifier", "")
    client_id = body.get("client_id", "")
    redirect_uri = body.get("redirect_uri")

    client = get_oauth_client(db, client_id) if client_id else None
    if client is None:
        raise HTTPException(status_code=400, detail="invalid_client")

    record = consume_auth_code(db, code, client_id)
    if record is None:
        raise HTTPException(status_code=400, detail="invalid_grant")

    if record.code_challenge != pkce_challenge(code_verifier or ""):
        raise HTTPException(status_code=400, detail="invalid_grant")

    if redirect_uri and redirect_uri != record.redirect_uri:
        raise HTTPException(status_code=400, detail="invalid_grant")

    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="invalid_grant")

    scopes = record.scopes.split() or [SCOPE]
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(
        db, client_id=client_id, user_id=user.id, scopes=scopes
    )
    return _token_response(access_token, refresh_token, scopes)


async def _token_from_refresh(body: dict, db: Session) -> JSONResponse:
    raw_refresh = body.get("refresh_token", "")

    record = consume_refresh_token(db, raw_refresh)
    if record is None:
        raise HTTPException(status_code=400, detail="invalid_grant")

    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="invalid_grant")

    scopes = record.scopes.split() or [SCOPE]
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(
        db, client_id=record.client_id, user_id=user.id, scopes=scopes
    )
    return _token_response(access_token, refresh_token, scopes)


def _token_response(access_token: str, refresh_token: str, scopes: list[str]) -> JSONResponse:
    from app.config import settings

    expires_in = int(getattr(settings, "jwt_access_expire_minutes", 15)) * 60
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": " ".join(scopes),
            "refresh_token": refresh_token,
        }
    )


@router.post("/oauth/revoke")
async def oauth_revoke(request: Request, db: Session = Depends(get_db)) -> Response:
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    else:
        form = await request.form()
        body = dict(form)
    raw = body.get("token", "")
    revoke_refresh_token(db, raw)
    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Backend login page for the authorize step
# ---------------------------------------------------------------------------


def _set_mcp_session_cookie(response: Response, token: str) -> None:
    """Issue the short-lived session cookie that authorizes the MCP flow."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=not _is_dev(),
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/oauth",
    )


def _sso_buttons_html(next_url: str, providers: list[SSOProviderSummary]) -> str:
    """Render SSO provider sign-in buttons for the login page."""
    safe_next = quote(_safe_next(next_url), safe="")
    buttons: list[str] = []
    for provider in providers:
        label = html.escape(provider.display_name or provider.provider)
        start_path = (
            "/oauth/sso/oidc/start" if provider.kind == "oidc" else "/oauth/sso/saml/start"
        )
        href = f"{start_path}/{quote(provider.provider, safe='')}?next={safe_next}"
        buttons.append(
            f'<a class="sso-btn" href="{href}">Continue with {label}</a>'
        )
    if not buttons:
        return ""
    return (
        '<div class="sso">'
        '<p class="sso-divider"><span>or</span></p>'
        + "".join(buttons)
        + "</div>"
    )


def _enabled_sso_providers(db: Session) -> list[SSOProviderSummary]:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        return []
    return list_enabled_providers(db)


def _login_page(*, next_url: str, error: str | None, db: Session) -> HTMLResponse:
    providers = _enabled_sso_providers(db)
    err_html = (
        '<p class="error">Invalid email or password.</p>' if error else ""
    )
    sso_html = _sso_buttons_html(next_url, providers) if providers else ""
    safe_next = html.escape(_safe_next(next_url), quote=True)
    page = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stockwire — Authorize MCP</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; display:flex; min-height:100vh; align-items:center; justify-content:center; }}
  .card {{ background:#1e293b; padding:2rem; border-radius:12px; width:340px; box-shadow:0 10px 30px rgba(0,0,0,.4); }}
  h1 {{ font-size:1.2rem; margin-top:0; }}
  label {{ display:block; margin:1rem 0 .25rem; font-size:.85rem; }}
  input {{ width:100%; padding:.55rem; border-radius:8px; border:1px solid #334155; background:#0f172a; color:#e2e8f0; box-sizing:border-box; }}
  button {{ margin-top:1.25rem; width:100%; padding:.6rem; border:0; border-radius:8px; background:#38bdf8; color:#0f172a; font-weight:600; cursor:pointer; }}
  .error {{ color:#f87171; font-size:.85rem; }}
  .sso {{ margin-top:1.5rem; }}
  .sso-divider {{ display:flex; align-items:center; color:#64748b; font-size:.8rem; }}
  .sso-divider::before, .sso-divider::after {{ content:""; flex:1; height:1px; background:#334155; }}
  .sso-divider span {{ padding:0 .75rem; }}
  .sso-btn {{ display:block; text-align:center; margin-top:.75rem; padding:.6rem; border-radius:8px; background:#334155; color:#e2e8f0; text-decoration:none; font-size:.9rem; }}
  .sso-btn:hover {{ background:#475569; }}
</style></head>
<body><div class="card">
  <h1>Sign in to authorize MCP</h1>
  <p style="font-size:.85rem;color:#94a3b8">This grants the AI assistant access to your Stockwire account.</p>
  {err_html}
  <form method="post" action="/oauth/login">
    <input type="hidden" name="next" value="{safe_next}">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" required autofocus>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" required>
    <button type="submit">Sign in</button>
  </form>
  {sso_html}
</div></body></html>"""
    return HTMLResponse(page)


@router.api_route("/oauth/login", methods=["GET", "POST"])
async def oauth_login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    if request.method == "GET":
        next_url = request.query_params.get("next")
        return _login_page(next_url=next_url or "/oauth/authorize", error=None, db=db)

    form = await request.form()
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", ""))
    next_url = str(form.get("next", "")) or "/oauth/authorize"

    user = db.scalar(select(User).where(User.email == email)) if email else None
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return _login_page(next_url=next_url, error="invalid", db=db)

    token = create_access_token(user.id, user.email, user.role)
    response = RedirectResponse(url=_safe_next(next_url), status_code=302)
    _set_mcp_session_cookie(response, token)
    return response


def _is_dev() -> bool:
    from app.config import settings

    return (getattr(settings, "app_env", "development") or "development").lower() in {
        "development",
        "dev",
        "local",
        "test",
    }


# ---------------------------------------------------------------------------
# SSO (OIDC / SAML) login for the authorize step
# ---------------------------------------------------------------------------
# These complement the local-password login above so SSO users can also obtain
# the ``mcp_session`` cookie and complete the MCP authorization flow. They reuse
# the same SSO plumbing as the SPA (app.domain.auth.sso) but, instead of
# returning a token to the SPA, set the ``mcp_session`` cookie and bounce the
# user back to the original ``/oauth/authorize`` URL.
#
# Operational note: the OIDC ``redirect_uri`` (the callback below) and the SAML
# ACS URL (the SAML callback below) must be registered with the respective IdP,
# just like the existing SPA SSO endpoints.


def _decode_saml_relay_state(relay_state: str) -> dict[str, Any]:
    if not relay_state:
        return {}
    try:
        decoded = base64.urlsafe_b64decode(relay_state.encode()).decode("utf-8")
        parsed = json.loads(decoded)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, base64.binascii.Error):
        return {}


@router.get("/oauth/sso/oidc/start/{provider}")
async def oauth_sso_oidc_start(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=404, detail="SSO not enabled")

    oidc = get_oidc_provider(provider, db)
    next_url = request.query_params.get("next") or "/oauth/authorize"
    safe_next = _safe_next(next_url)
    callback_uri = (
        f"{mcp_issuer_url()}/oauth/sso/oidc/callback"
        f"?provider={quote(provider, safe='')}&next={quote(safe_next, safe='')}"
    )
    authorize_url, state = build_oidc_authorize_url(oidc, callback_uri)

    response = RedirectResponse(url=authorize_url, status_code=302)
    # Bind the state to the browser session (HttpOnly) so the callback can verify
    # the round trip originated here (CSRF protection).
    response.set_cookie(
        key="oidc_state",
        value=state,
        httponly=True,
        secure=not _is_dev(),
        samesite="lax",
        path="/oauth",
        max_age=600,
    )
    return response


@router.get("/oauth/sso/oidc/callback")
async def oauth_sso_oidc_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=404, detail="SSO not enabled")

    params = request.query_params
    provider = params.get("provider", "")
    code = params.get("code", "")
    state = params.get("state")
    next_url = params.get("next") or "/oauth/authorize"
    safe_next = _safe_next(next_url)

    expected_state = request.cookies.get("oidc_state")
    if not verify_oidc_state(state, expected_state):
        raise HTTPException(status_code=403, detail="Invalid or expired OIDC state")

    oidc = get_oidc_provider(provider, db)
    # Reconstruct the exact redirect_uri used at start so the IdP accepts the
    # token exchange (it must match what was sent in the authorize request).
    callback_uri = (
        f"{mcp_issuer_url()}/oauth/sso/oidc/callback"
        f"?provider={quote(provider, safe='')}&next={quote(safe_next, safe='')}"
    )
    claims = exchange_oidc_code(oidc, code, callback_uri)
    identity = claims_to_identity(oidc, claims)
    user = upsert_external_user(
        db,
        provider_key=oidc.key,
        source="oidc",
        subject=identity["subject"],
        email=identity["email"],
        full_name=identity["full_name"],
        groups=identity["groups"],
        allow_auto_create=oidc.allow_auto_create,
        runtime=runtime,
    )

    token = create_access_token(user.id, user.email, user.role)
    response = RedirectResponse(url=safe_next, status_code=302)
    _set_mcp_session_cookie(response, token)
    response.delete_cookie("oidc_state", path="/oauth")
    return response


@router.get("/oauth/sso/saml/start/{provider}")
async def oauth_sso_saml_start(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=404, detail="SSO not enabled")

    saml = get_saml_provider(provider, db)
    next_url = request.query_params.get("next") or "/oauth/authorize"
    safe_next = _safe_next(next_url)
    relay_state = (
        base64.urlsafe_b64encode(
            json.dumps({"provider": saml.key, "redirect": safe_next}).encode()
        )
        .decode()
        .rstrip("=")
    )
    separator = "&" if "?" in saml.idp_sso_url else "?"
    redirect_url = f"{saml.idp_sso_url}{separator}RelayState={quote(relay_state, safe='')}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/oauth/sso/saml/callback")
async def oauth_sso_saml_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=404, detail="SSO not enabled")

    form = await request.form()
    saml_response = str(form.get("SAMLResponse", ""))
    relay_state = str(form.get("RelayState", ""))
    state = _decode_saml_relay_state(relay_state)
    provider_key = state.get("provider")
    if not provider_key:
        raise HTTPException(status_code=400, detail="Invalid SAML relay state")

    redirect = state.get("redirect")
    safe_next = _safe_next(redirect) if redirect else "/oauth/authorize"

    saml = get_saml_provider(provider_key, db)
    identity = parse_saml_response(saml, saml_response)
    user = upsert_external_user(
        db,
        provider_key=saml.key,
        source="saml",
        subject=identity["subject"],
        email=identity["email"],
        full_name=identity["full_name"],
        groups=identity["groups"],
        allow_auto_create=saml.allow_auto_create,
        runtime=runtime,
    )

    token = create_access_token(user.id, user.email, user.role)
    response = RedirectResponse(url=safe_next, status_code=302)
    _set_mcp_session_cookie(response, token)
    return response
