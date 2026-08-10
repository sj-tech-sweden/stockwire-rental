import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.config import settings
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import User, UserSession, APIKey, Role, UserRole
from app.domain.auth.schemas import Token, UserCreate, UserLogin, UserSummary, UserSelfUpdate, OIDCExchangeRequest, SAMLAssertionRequest, SSOProviderSummary, ForgotPasswordRequest, ResetPasswordRequest
from app.domain.auth.security import create_access_token, generate_refresh_token, compute_refresh_token_hash, hash_password, verify_password, hash_api_key, hash_api_key_lookup, decode_token
from app.domain.auth.sso import (
    build_oidc_authorize_url,
    verify_oidc_state,
    claims_to_identity,
    exchange_oidc_code,
    get_runtime_sso_config,
    get_oidc_provider,
    get_saml_provider,
    list_enabled_providers,
    parse_saml_response,
    upsert_external_user,
)
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(key_func=get_remote_address)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.jwt_refresh_expire_days * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        path="/api/v1/auth",
        max_age=max_age,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        samesite="none",
        secure=True,
        path="/api/v1/auth",
        max_age=0,
    )


def _create_refresh_session(db: Session, user: User) -> str:
    refresh_token = generate_refresh_token()
    token_hash = compute_refresh_token_hash(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    session = UserSession(
        session_id=token_hash,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return refresh_token


def _make_token_response(user: User, response: Response, db: Session) -> Token:
    access_token_str = create_access_token(user.id, user.email, user.role)
    refresh_token = _create_refresh_session(db, user)
    _set_refresh_cookie(response, refresh_token)
    token = Token(access_token=access_token_str, user=UserSummary.model_validate(user))
    token.refresh_token = refresh_token
    return token


@router.get("/sso/providers", response_model=list[SSOProviderSummary])
def sso_providers(db: Session = Depends(get_db)) -> list[SSOProviderSummary]:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        return []
    return list_enabled_providers(db)


@router.get("/sso/saml-provider-config/{provider}")
def saml_provider_config(provider: str, db: Session = Depends(get_db)) -> dict:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")
    saml = get_saml_provider(provider, db)
    return {
        "provider": saml.key,
        "kind": "saml",
        "display_name": saml.display_name,
        "enabled": saml.enabled,
        "auto_create_users": saml.allow_auto_create,
        "idp_entity_id": saml.idp_entity_id,
        "idp_sso_url": saml.idp_sso_url,
        "sp_entity_id": saml.sp_entity_id,
        "acs_url": saml.acs_url,
    }


@router.get("/sso/oidc/authorize/{provider}")
def oidc_authorize(
    provider: str,
    redirect_uri: str,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")
    oidc = get_oidc_provider(provider, db)
    if not redirect_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri is required")
    authorize_url, state = build_oidc_authorize_url(oidc, redirect_uri)
    # Bind the state to the browser session via a Secure, HttpOnly, SameSite cookie
    # so that the exchange endpoint can verify the state originated from this browser.
    response.set_cookie(
        key="oidc_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    return {"authorize_url": authorize_url, "state": state}


@router.post("/sso/oidc/exchange", response_model=Token)
def oidc_exchange(
    payload: OIDCExchangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Token:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")

    # Verify OIDC state parameter to prevent CSRF attacks.
    # Use the state stored in the HttpOnly cookie as the expected value so the
    # state is bound to the browser session that initiated the authorize request.
    expected_state = request.cookies.get("oidc_state")
    if not verify_oidc_state(payload.state, expected_state):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired OIDC state")
    # Clear the one-time state cookie after successful verification
    response.delete_cookie("oidc_state")

    oidc = get_oidc_provider(payload.provider, db)
    claims = exchange_oidc_code(oidc, payload.code, payload.redirect_uri)
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
    return _make_token_response(user, response, db)


@router.post("/sso/saml/login", response_model=Token)
def saml_login(payload: SAMLAssertionRequest, response: Response, db: Session = Depends(get_db)) -> Token:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")

    saml = get_saml_provider(payload.provider, db)
    identity = parse_saml_response(saml, payload.saml_response)
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
    return _make_token_response(user, response, db)


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)) -> dict:
    """Returns whether first-time setup is still needed (no users exist)."""
    count = db.scalar(select(func.count()).select_from(User))
    return {"setup_needed": count == 0}


@router.post("/setup", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def setup_admin(request: Request, payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> Token:
    """Create the first admin account. Only works when no users exist."""
    count = db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Setup already complete")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="admin",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _make_token_response(user, response, db)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> Token:
    identifier = str(payload.email or "").strip().lower()
    user = None

    if identifier:
        # Try exact email first.
        user = db.scalar(select(User).where(func.lower(User.email) == identifier))

    if user is None and identifier and "@" not in identifier:
        # Backward-compatible convenience: allow login by email local-part (before @) when unique.
        matches = list(
            db.scalars(
                select(User).where(func.lower(User.email).like(f"{identifier}@%"))
            ).all()
        )
        if len(matches) == 1:
            user = matches[0]

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    password_ok = verify_password(payload.password, user.password_hash)
    if not password_ok and payload.password == user.password_hash:
        # Auto-upgrade legacy plaintext seed passwords to bcrypt hash on first successful login.
        user.password_hash = hash_password(payload.password)
        db.add(user)
        db.commit()
        db.refresh(user)
        password_ok = True

    if not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return _make_token_response(user, response, db)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    normalized_email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is None:
        return

    reset_token = jwt.encode(
        {
            "sub": str(user.id),
            "purpose": "password_reset",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    reset_url = f"{settings.password_reset_base_url}/reset-password/{reset_token}"

    try:
        from app.services.email import EmailMessage, send_email

        send_email(
            EmailMessage(
                to=user.email,
                subject="Password Reset Request",
                text_body=f"Click the following link to reset your password: {reset_url}",
                html_body=_build_password_reset_email(reset_url),
            ),
            db=db,
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)


def _build_password_reset_email(reset_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding: 40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; overflow: hidden;">
        <tr><td style="padding: 32px 40px; background: #1976d2;">
          <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Stockwire Rental</h1>
        </td></tr>
        <tr><td style="padding: 32px 40px;">
          <h2 style="color: #333; margin: 0 0 16px;">Password Reset Request</h2>
          <p style="color: #555; line-height: 1.6; margin: 0 0 24px;">
            You recently requested to reset your password. Click the button below to choose a new one.
            This link expires in {settings.password_reset_expire_minutes} minutes.
          </p>
          <table cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="background: #1976d2; border-radius: 4px;">
                <a href="{reset_url}" style="display: inline-block; padding: 12px 32px; color: #ffffff; text-decoration: none; font-size: 16px;">Reset Password</a>
              </td>
            </tr>
          </table>
          <p style="color: #999; font-size: 13px; margin: 24px 0 0;">
            If you did not request a password reset, please ignore this email.
          </p>
        </td></tr>
        <tr><td style="padding: 16px 40px; background: #f4f4f4; text-align: center;">
          <p style="color: #999; font-size: 12px; margin: 0;">&copy; Stockwire Rental &mdash; All rights reserved.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    try:
        claims = decode_token(payload.token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if claims.get("purpose") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token purpose")

    user_id = int(claims["sub"])
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()


@router.post("/refresh", response_model=Token)
def refresh_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    refresh_token = request.cookies.get("refresh_token") or request.headers.get("X-Refresh-Token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    token_hash = compute_refresh_token_hash(refresh_token)
    session = db.get(UserSession, token_hash)
    if session is None:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        db.delete(session)
        db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    db.delete(session)
    db.commit()

    new_token = create_access_token(user.id, user.email, user.role)
    new_refresh = _create_refresh_session(db, user)
    _set_refresh_cookie(response, new_refresh)

    result = Token(access_token=new_token, user=UserSummary.model_validate(user))
    result.refresh_token = new_refresh
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_hash = compute_refresh_token_hash(refresh_token)
        session = db.get(UserSession, token_hash)
        if session is not None:
            db.delete(session)
            db.commit()
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me", response_model=UserSummary)
def update_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    auth_source = str(current_user.auth_source or "local").strip().lower()
    if auth_source in {"oidc", "saml"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile updates are managed by your SSO provider",
        )

    normalized_email = str(payload.email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")

    existing = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    current_user.email = normalized_email
    current_user.full_name = str(payload.full_name or "").strip() or current_user.full_name
    current_user.notification_channel = payload.notification_channel

    new_password = str(payload.password or "").strip()
    if new_password:
        current_user.password_hash = hash_password(new_password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users", response_model=list[UserSummary])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.post("/users", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        notification_channel=payload.notification_channel,
        is_active=payload.is_active,
        is_admin=payload.role == "admin",
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserSummary)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserSummary)
def update_user(
    user_id: int,
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Update fields
    user.email = payload.email
    if payload.password:
        user.password_hash = hash_password(payload.password)
    user.full_name = payload.full_name
    user.role = payload.role
    user.is_active = payload.is_active
    user.is_admin = payload.role == "admin"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Schemas for API keys and roles
class APIKeyCreate(BaseModel):
    name: str
    is_admin: bool = False
    raw_key: str


class APIKeyOut(BaseModel):
    id: int
    name: str
    is_admin: bool
    created_at: datetime


@router.get("/api-keys", response_model=list[APIKeyOut])
def list_api_keys(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return list(db.scalars(select(APIKey).where(APIKey.is_active.is_(True)).order_by(APIKey.id)).all())


@router.post("/api-keys", response_model=APIKeyOut, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: APIKeyCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    # Store only the hash
    api_lookup = hash_api_key_lookup(payload.raw_key)
    api_hash = hash_api_key(payload.raw_key)
    ak = APIKey(name=payload.name, api_key_lookup=api_lookup, api_key_hash=api_hash, is_active=True, is_admin=payload.is_admin)
    db.add(ak)
    db.commit()
    db.refresh(ak)
    return ak


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(key_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ak = db.get(APIKey, key_id)
    if ak is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    ak.is_active = False
    db.add(ak)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class RoleCreate(BaseModel):
    name: str
    display_name: str | None = None
    permissions: list[str] | None = None


class RoleAssign(BaseModel):
    role_id: int


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Role).order_by(Role.id)).all())


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    role = Role(name=payload.name, display_name=payload.display_name, permissions=payload.permissions or [])
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


# User role assignment endpoints
@router.get("/users/{user_id}/roles")
def list_user_roles(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return [r for r in user.roles]


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
def assign_role_to_user(user_id: int, payload: RoleAssign, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = db.get(Role, payload.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    # Create user_roles mapping if not exists
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has role")
    ur = UserRole(user_id=user_id, role_id=role.id, is_active=True)
    db.add(ur)
    db.commit()
    return role


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role_from_user(user_id: int, role_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ur = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if ur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
    db.delete(ur)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
