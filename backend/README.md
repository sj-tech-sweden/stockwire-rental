# Backend

FastAPI backend for Stockwire Rental.

## Run locally

```bash
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
pytest
```

## Migrations

```bash
alembic upgrade head
```

## API key hashing migration note

API keys are now verified only against PBKDF2-based hashes.

- Legacy API keys stored with the older HMAC-SHA256 hash format are no longer accepted.
- Existing legacy API keys must be regenerated and re-created through the API key admin flow.
- `API_KEY_PEPPER` is required unless `APP_ENV` is explicitly set to `development` or `test`.

## Seed demo data

```bash
python scripts/seed_demo.py
```

## OIDC / SAML SSO

The backend supports external sign-in via OIDC and SAML.

Core env flags:

- `SSO_ENABLED=true|false`
- `SSO_AUTO_CREATE_USERS=true|false`
- `SSO_SYNC_ROLES_ON_LOGIN=true|false`
- `SSO_DEFAULT_ROLE=viewer`
- `SSO_GROUP_ROLE_MAP={"GroupA":"admin","GroupB":"manager"}`

Provider config:

- `OIDC_PROVIDERS` JSON object keyed by provider name
- `SAML_PROVIDERS` JSON object keyed by provider name

See `infra/env/.env.example` for full Entra ID and Keycloak examples.

API endpoints:

- `GET /api/v1/auth/sso/providers`
- `GET /api/v1/auth/sso/oidc/authorize/{provider}?redirect_uri=...`
- `POST /api/v1/auth/sso/oidc/exchange`
- `POST /api/v1/auth/sso/saml/login`

Group-to-role mapping:

1. Groups from OIDC/SAML claim/attribute are matched against `SSO_GROUP_ROLE_MAP`.
2. Highest role wins (`admin > manager > viewer`).
3. If no mapping matches, `SSO_DEFAULT_ROLE` is applied.

Auto-provisioning behavior:

- If `allow_auto_create` is `false` on a provider (or global `SSO_AUTO_CREATE_USERS=false`), sign-in only works for pre-existing users.
- Existing users can still authenticate and optionally get role updates on login when `SSO_SYNC_ROLES_ON_LOGIN=true`.

Provider setup guides:

- Entra ID: `../docs/SSO_ENTRA_ID_GUIDE.md`
- Keycloak: `../docs/SSO_KEYCLOAK_GUIDE.md`
- Storage and uploads: `../docs/STORAGE_FILES_GUIDE.md`
