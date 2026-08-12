from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.auth.models import Role, User
from app.domain.auth.schemas import SSOProviderSummary
from app.domain.auth.security import hash_password
from app.domain.settings.models import AppSetting


VALID_ROLES = {"admin", "manager", "viewer"}
_ROLE_PRIORITY = {"admin": 3, "manager": 2, "viewer": 1}
SSO_SETTINGS_KEY = "auth.sso"

# State expiry: 5 minutes
_OIDC_STATE_EXPIRY_SECONDS = 300


@dataclass
class OIDCProvider:
    key: str
    display_name: str
    issuer: str
    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    scopes: str
    group_claim: str
    email_claim: str
    name_claim: str
    subject_claim: str
    allow_auto_create: bool
    enabled: bool


@dataclass
class SAMLProvider:
    key: str
    display_name: str
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    sp_entity_id: str
    acs_url: str
    group_attribute: str
    email_attribute: str
    name_attribute: str
    subject_attribute: str
    allow_auto_create: bool
    enabled: bool


@dataclass
class SSORuntimeConfig:
    enabled: bool
    auto_create_users: bool
    sync_roles_on_login: bool
    default_role: str
    group_role_map: dict[str, str]
    oidc_providers: dict[str, dict[str, Any]]
    saml_providers: dict[str, dict[str, Any]]


def default_sso_settings_payload() -> dict[str, Any]:
    oidc = []
    for key, value in settings.oidc_providers_obj.items():
        oidc.append({"key": key, **value})
    saml = []
    for key, value in settings.saml_providers_obj.items():
        saml.append({"key": key, **value})

    return {
        "enabled": bool(settings.sso_enabled),
        "auto_create_users": bool(settings.sso_auto_create_users),
        "sync_roles_on_login": bool(settings.sso_sync_roles_on_login),
        "default_role": str(settings.sso_default_role or "viewer").lower(),
        "group_role_map": settings.sso_group_role_map_obj,
        "oidc_providers": oidc,
        "saml_providers": saml,
    }


def normalize_sso_settings_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    defaults = default_sso_settings_payload()

    default_role = str(source.get("default_role") or defaults.get("default_role") or "viewer").strip().lower()
    if default_role not in VALID_ROLES:
        default_role = "viewer"

    role_map_raw = source.get("group_role_map") if isinstance(source.get("group_role_map"), dict) else {}
    role_map: dict[str, str] = {}
    for key, value in role_map_raw.items():
        group_name = str(key or "").strip()
        role_name = str(value or "").strip().lower()
        if group_name and role_name in VALID_ROLES:
            role_map[group_name] = role_name

    oidc_list = _normalize_provider_list(source.get("oidc_providers"), kind="oidc")
    saml_list = _normalize_provider_list(source.get("saml_providers"), kind="saml")

    return {
        "enabled": bool(source.get("enabled", defaults.get("enabled", False))),
        "auto_create_users": bool(source.get("auto_create_users", defaults.get("auto_create_users", True))),
        "sync_roles_on_login": bool(source.get("sync_roles_on_login", defaults.get("sync_roles_on_login", True))),
        "default_role": default_role,
        "group_role_map": role_map,
        "oidc_providers": oidc_list,
        "saml_providers": saml_list,
    }


def _normalize_provider_list(raw: Any, *, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source: list[dict[str, Any]] = []

    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                source.append({"key": str(key), **value})
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                source.append(item)

    seen: set[str] = set()
    for item in source:
        key = str(item.get("key") or item.get("provider") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized = {k: v for k, v in item.items() if k not in {"key", "provider", "kind"}}
        normalized["key"] = key
        normalized["kind"] = kind
        normalized["display_name"] = str(normalized.get("display_name") or key)
        normalized["enabled"] = bool(normalized.get("enabled", True))
        rows.append(normalized)

    return rows


def _providers_list_to_map(rows: list[dict[str, Any]], *, kind: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in rows:
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        row = {k: v for k, v in item.items() if k not in {"key", "kind"}}
        row["kind"] = kind
        out[key] = row
    return out


def get_runtime_sso_config(db: Session | None = None) -> SSORuntimeConfig:
    normalized = default_sso_settings_payload()
    if db is not None:
        setting = db.scalar(select(AppSetting).where(AppSetting.key == SSO_SETTINGS_KEY))
        if setting and setting.value_json:
            try:
                persisted_raw = json.loads(setting.value_json)
            except Exception:
                persisted_raw = {}
            normalized = normalize_sso_settings_payload(persisted_raw)
        else:
            normalized = normalize_sso_settings_payload(normalized)
    else:
        normalized = normalize_sso_settings_payload(normalized)

    return SSORuntimeConfig(
        enabled=bool(normalized.get("enabled", False)),
        auto_create_users=bool(normalized.get("auto_create_users", True)),
        sync_roles_on_login=bool(normalized.get("sync_roles_on_login", True)),
        default_role=str(normalized.get("default_role") or "viewer"),
        group_role_map=normalized.get("group_role_map") if isinstance(normalized.get("group_role_map"), dict) else {},
        oidc_providers=_providers_list_to_map(normalized.get("oidc_providers") if isinstance(normalized.get("oidc_providers"), list) else [], kind="oidc"),
        saml_providers=_providers_list_to_map(normalized.get("saml_providers") if isinstance(normalized.get("saml_providers"), list) else [], kind="saml"),
    )


def _json_http(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url=url, data=data, headers=headers, method=method.upper())
    with urlopen(req, timeout=10) as resp:  # nosec B310 - configured IdP endpoints only
        content = resp.read().decode("utf-8")
    decoded = json.loads(content or "{}")
    return decoded if isinstance(decoded, dict) else {}


def _form_http(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = urlencode(payload).encode("utf-8")
    req = Request(
        url=url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:  # nosec B310 - configured IdP endpoints only
        content = resp.read().decode("utf-8")
    decoded = json.loads(content or "{}")
    return decoded if isinstance(decoded, dict) else {}


def _first(values: Any, fallback: str = "") -> str:
    if isinstance(values, list):
        if not values:
            return fallback
        return str(values[0] or fallback)
    if values is None:
        return fallback
    return str(values)


def _normalize_groups(groups: Any) -> list[str]:
    if groups is None:
        return []
    if isinstance(groups, str):
        return [groups]
    if isinstance(groups, list):
        return [str(v) for v in groups if v is not None]
    return []


def _parse_oidc_provider(key: str, raw: dict[str, Any], runtime: SSORuntimeConfig) -> OIDCProvider:
    return OIDCProvider(
        key=key,
        display_name=str(raw.get("display_name") or key),
        issuer=str(raw.get("issuer") or "").strip(),
        client_id=str(raw.get("client_id") or "").strip(),
        client_secret=str(raw.get("client_secret") or "").strip(),
        authorization_endpoint=str(raw.get("authorization_endpoint") or "").strip(),
        token_endpoint=str(raw.get("token_endpoint") or "").strip(),
        jwks_uri=str(raw.get("jwks_uri") or "").strip(),
        scopes=str(raw.get("scopes") or "openid profile email"),
        group_claim=str(raw.get("group_claim") or "groups"),
        email_claim=str(raw.get("email_claim") or "email"),
        name_claim=str(raw.get("name_claim") or "name"),
        subject_claim=str(raw.get("subject_claim") or "sub"),
        allow_auto_create=bool(raw.get("allow_auto_create", runtime.auto_create_users)),
        enabled=bool(raw.get("enabled", True)),
    )


def _parse_saml_provider(key: str, raw: dict[str, Any], runtime: SSORuntimeConfig) -> SAMLProvider:
    return SAMLProvider(
        key=key,
        display_name=str(raw.get("display_name") or key),
        idp_entity_id=str(raw.get("idp_entity_id") or "").strip(),
        idp_sso_url=str(raw.get("idp_sso_url") or "").strip(),
        idp_x509_cert=str(raw.get("idp_x509_cert") or "").strip(),
        sp_entity_id=str(raw.get("sp_entity_id") or "").strip(),
        acs_url=str(raw.get("acs_url") or "").strip(),
        group_attribute=str(raw.get("group_attribute") or "groups"),
        email_attribute=str(raw.get("email_attribute") or "email"),
        name_attribute=str(raw.get("name_attribute") or "displayName"),
        subject_attribute=str(raw.get("subject_attribute") or "nameid"),
        allow_auto_create=bool(raw.get("allow_auto_create", runtime.auto_create_users)),
        enabled=bool(raw.get("enabled", True)),
    )


def get_oidc_provider(provider: str, db: Session | None = None) -> OIDCProvider:
    runtime = get_runtime_sso_config(db)
    raw = runtime.oidc_providers.get(provider)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC provider not configured")
    parsed = _parse_oidc_provider(provider, raw, runtime)
    if not parsed.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OIDC provider disabled")
    return parsed


def get_saml_provider(provider: str, db: Session | None = None) -> SAMLProvider:
    runtime = get_runtime_sso_config(db)
    raw = runtime.saml_providers.get(provider)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SAML provider not configured")
    parsed = _parse_saml_provider(provider, raw, runtime)
    if not parsed.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SAML provider disabled")
    return parsed


def list_enabled_providers(db: Session | None = None) -> list[SSOProviderSummary]:
    runtime = get_runtime_sso_config(db)
    out: list[SSOProviderSummary] = []
    for key, raw in runtime.oidc_providers.items():
        provider = _parse_oidc_provider(key, raw, runtime)
        if not provider.enabled:
            continue
        out.append(
            SSOProviderSummary(
                provider=provider.key,
                kind="oidc",
                display_name=provider.display_name,
                enabled=provider.enabled,
                auto_create_users=provider.allow_auto_create,
            )
        )
    for key, raw in runtime.saml_providers.items():
        provider = _parse_saml_provider(key, raw, runtime)
        if not provider.enabled:
            continue
        out.append(
            SSOProviderSummary(
                provider=provider.key,
                kind="saml",
                display_name=provider.display_name,
                enabled=provider.enabled,
                auto_create_users=provider.allow_auto_create,
            )
        )
    return out


def _sign_state(token: str, timestamp: int) -> str:
    """Create a HMAC signature for the OIDC state parameter."""
    message = f"{token}:{timestamp}".encode("utf-8")
    key = settings.jwt_secret_key.encode("utf-8")
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    return signature


def build_oidc_authorize_url(provider: OIDCProvider, redirect_uri: str) -> tuple[str, str]:
    """Build OIDC authorization URL and return (url, state) for CSRF verification."""
    token = secrets.token_urlsafe(16)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    signature = _sign_state(token, timestamp)
    # State format: base64(token:timestamp:signature)
    state_payload = f"{token}:{timestamp}:{signature}"
    state = base64.urlsafe_b64encode(state_payload.encode()).decode().rstrip("=")
    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "scope": provider.scopes,
        "redirect_uri": redirect_uri,
        "state": state,
        "nonce": secrets.token_urlsafe(16),
    }
    return f"{provider.authorization_endpoint}?{urlencode(params)}", state


def verify_oidc_state(provided_state: str | None, expected_state: str | None) -> bool:
    """Verify that the OIDC state parameter matches and hasn't expired.

    If a cookie-based expected_state is available (same-origin / HTTPS), it must
    match the provided state.  When the cookie is absent (cross-origin HTTP with
    SameSite=Lax), we fall through to HMAC verification — the signature already
    proves the state was issued by this backend and the expiry limits replay.
    """
    if not provided_state:
        return False

    try:
        # If the cookie was sent, enforce exact match (defense-in-depth).
        if expected_state is not None and not hmac.compare_digest(provided_state, expected_state):
            return False

        # Pad the base64 string (urlsafe) to a multiple of 4 characters
        missing_padding = (-len(provided_state)) % 4
        padded = provided_state + ("=" * missing_padding)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) != 3:
            return False

        token, timestamp_str, provided_signature = parts
        timestamp = int(timestamp_str)

        # Check expiry
        now = int(datetime.now(timezone.utc).timestamp())
        if now - timestamp > _OIDC_STATE_EXPIRY_SECONDS:
            return False

        # Verify HMAC signature (proves state was generated by this backend)
        expected_signature = _sign_state(token, timestamp)
        return hmac.compare_digest(provided_signature, expected_signature)
    except Exception:
        return False


def exchange_oidc_code(provider: OIDCProvider, code: str, redirect_uri: str) -> dict[str, Any]:
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    token_data = _form_http(provider.token_endpoint, token_payload)
    id_token = str(token_data.get("id_token") or "").strip()
    if not id_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing id_token in OIDC token response")

    jwks = _json_http("GET", provider.jwks_uri)
    keys = jwks.get("keys") if isinstance(jwks.get("keys"), list) else []
    if not keys:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OIDC JWKS fetch failed")

    claims: dict[str, Any] | None = None
    for key in keys:
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                audience=provider.client_id,
                issuer=provider.issuer,
            )
            break
        except Exception:
            continue

    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OIDC token")

    if int(claims.get("exp", 0) or 0) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired OIDC token")

    return claims


def resolve_role_from_groups(groups: list[str], runtime: SSORuntimeConfig) -> str:
    mapping = runtime.group_role_map
    if not mapping:
        return runtime.default_role

    best_role = runtime.default_role
    best_score = _ROLE_PRIORITY.get(best_role, 0)
    lower_map = {k.lower(): v.lower() for k, v in mapping.items()}
    for raw in groups:
        role = lower_map.get(str(raw).strip().lower())
        if not role or role not in VALID_ROLES:
            continue
        score = _ROLE_PRIORITY.get(role, 0)
        if score > best_score:
            best_score = score
            best_role = role
    return best_role


def _find_existing_user(db: Session, provider_key: str, subject: str, email: str) -> User | None:
    if provider_key and subject:
        existing = db.scalar(
            select(User).where(
                User.external_provider == provider_key,
                User.external_subject == subject,
            )
        )
        if existing is not None:
            return existing

    if email:
        return db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    return None


def upsert_external_user(
    db: Session,
    *,
    provider_key: str,
    source: str,
    subject: str,
    email: str,
    full_name: str,
    groups: list[str],
    allow_auto_create: bool,
    runtime: SSORuntimeConfig,
) -> User:
    desired_role = resolve_role_from_groups(groups, runtime)
    existing = _find_existing_user(db, provider_key, subject, email)

    if existing is None and not allow_auto_create:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO account is not provisioned and auto-create is disabled",
        )

    if existing is None:
        existing = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            full_name=full_name or email,
            role=desired_role,
            is_active=True,
            is_admin=desired_role == "admin",
            auth_source=source,
            external_provider=provider_key,
            external_subject=subject,
            created_at=datetime.now(timezone.utc),
        )
        db.add(existing)
    else:
        existing.auth_source = source
        if provider_key and subject:
            existing.external_provider = provider_key
            existing.external_subject = subject
        if full_name and full_name != existing.full_name:
            existing.full_name = full_name

    if runtime.sync_roles_on_login and desired_role in VALID_ROLES:
        existing.role = desired_role
        existing.is_admin = desired_role == "admin"

    db.commit()
    db.refresh(existing)

    if not existing.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    _ensure_mapped_role_exists(db, existing, desired_role)
    return existing


def _ensure_mapped_role_exists(db: Session, user: User, role_name: str) -> None:
    if role_name not in VALID_ROLES:
        return
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        return
    if any(r.id == role.id for r in user.roles):
        return
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)


def parse_saml_response(provider: SAMLProvider, saml_response: str) -> dict[str, Any]:
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML support requires python3-saml package",
        ) from exc

    request_data = {
        "https": "on",
        "http_host": "localhost",
        "server_port": "443",
        "script_name": provider.acs_url,
        "get_data": {},
        "post_data": {"SAMLResponse": saml_response},
    }

    saml_settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": provider.sp_entity_id,
            "assertionConsumerService": {
                "url": provider.acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": {
            "entityId": provider.idp_entity_id,
            "singleSignOnService": {
                "url": provider.idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": provider.idp_x509_cert,
        },
    }

    auth = OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid SAML response: {','.join(errors)}")
    if not auth.is_authenticated():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SAML authentication failed")

    attrs = auth.get_attributes() or {}
    subject = auth.get_nameid() or _first(attrs.get(provider.subject_attribute))
    email = _first(attrs.get(provider.email_attribute), fallback=subject)
    full_name = _first(attrs.get(provider.name_attribute), fallback=email)
    groups = _normalize_groups(attrs.get(provider.group_attribute))

    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing SAML subject")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing SAML email")

    return {
        "subject": subject,
        "email": email,
        "full_name": full_name,
        "groups": groups,
    }


def claims_to_identity(provider: OIDCProvider, claims: dict[str, Any]) -> dict[str, Any]:
    subject = str(claims.get(provider.subject_claim) or "").strip()
    email = str(claims.get(provider.email_claim) or claims.get("email") or "").strip()
    full_name = str(claims.get(provider.name_claim) or claims.get("name") or email).strip()
    groups = _normalize_groups(claims.get(provider.group_claim))

    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OIDC subject claim")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OIDC email claim")

    return {
        "subject": subject,
        "email": email,
        "full_name": full_name,
        "groups": groups,
    }
