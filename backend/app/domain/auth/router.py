from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import User
from app.domain.auth.schemas import Token, UserCreate, UserLogin, UserSummary, UserSelfUpdate, OIDCExchangeRequest, SAMLAssertionRequest, SSOProviderSummary
from app.domain.auth.security import create_access_token, hash_password, verify_password, hash_api_key, hash_api_key_lookup
from app.domain.auth.sso import (
    build_oidc_authorize_url,
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
from app.domain.auth.models import APIKey, Role
from sqlalchemy import insert
from app.domain.auth.models import UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


def _make_token(user: User) -> Token:
    token = create_access_token(user.id, user.email, user.role)
    return Token(access_token=token, user=UserSummary.model_validate(user))


@router.get("/sso/providers", response_model=list[SSOProviderSummary])
def sso_providers(db: Session = Depends(get_db)) -> list[SSOProviderSummary]:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        return []
    return list_enabled_providers(db)


@router.get("/sso/oidc/authorize/{provider}")
def oidc_authorize(provider: str, redirect_uri: str, db: Session = Depends(get_db)) -> dict:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")
    oidc = get_oidc_provider(provider, db)
    if not redirect_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri is required")
    return {"authorize_url": build_oidc_authorize_url(oidc, redirect_uri)}


@router.post("/sso/oidc/exchange", response_model=Token)
def oidc_exchange(payload: OIDCExchangeRequest, db: Session = Depends(get_db)) -> Token:
    runtime = get_runtime_sso_config(db)
    if not runtime.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")

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
    return _make_token(user)


@router.post("/sso/saml/login", response_model=Token)
def saml_login(payload: SAMLAssertionRequest, db: Session = Depends(get_db)) -> Token:
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
    return _make_token(user)


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)) -> dict:
    """Returns whether first-time setup is still needed (no users exist)."""
    count = db.scalar(select(func.count()).select_from(User))
    return {"setup_needed": count == 0}


@router.post("/setup", response_model=Token, status_code=status.HTTP_201_CREATED)
def setup_admin(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
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
    return _make_token(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
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
    return _make_token(user)


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
    return list(db.scalars(select(APIKey).order_by(APIKey.id)).all())


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
