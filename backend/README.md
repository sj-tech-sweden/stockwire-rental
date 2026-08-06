# Backend

FastAPI backend for Stockwire Rental.

> Last reviewed: 2026-08-06

## Quick Start (Docker)

```bash
# From repo root
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env up -d backend
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend alembic upgrade head
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend python scripts/seed_demo.py
```

## Run Locally

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Specific file
pytest tests/test_api_crud.py -v
```

See [Testing Guide](../docs/TESTING_GUIDE.md) for details.

## Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## API Key Hashing Migration Note

API keys are now verified using PBKDF2-HMAC-SHA256 with a per-key random salt
and an indexed PBKDF2 lookup digest (`api_key_lookup` column, derived with 1
iteration keyed by `API_KEY_PEPPER`).

**Breaking change:** Legacy API keys stored with the older HMAC-SHA256 hash
format are no longer accepted. Such keys must be deleted and re-created through
the API key admin flow.

### Migration History

| Migration | Purpose |
|-----------|---------|
| `20260525_0021` | Adds `api_key_lookup` column (indexed, nullable) |
| `20260526_0022` | Resets `api_key_lookup` to `NULL` for re-backfill |
| `20260526_0023` | Resets `api_key_lookup` to `NULL` for final PBKDF2 digest |

After running all migrations, any PBKDF2-format key whose `api_key_lookup` is
`NULL` will authenticate via the NULL-scan fallback and have its lookup digest
backfilled automatically on first use.

### Required Environment Variables

- `API_KEY_PEPPER` - Required unless `APP_ENV` is `development` or `test`
- `PASSWORD_PEPPER` - Required unless `APP_ENV` is `development` or `test`
- `API_KEY_PBKDF2_ITERATIONS` - Verification iterations (default: 310,000)

## Seed Demo Data

```bash
python scripts/seed_demo.py
```

Creates:
- Admin user (admin@stockwire.app / admin)
- Sample products and devices
- Demo job with requirements
- Sample financial transactions

## API Documentation

When running, access auto-generated API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Metrics / Observability

Prometheus metrics are available at `/metrics`:

```bash
# Enable metrics
PROMETHEUS_ENABLED=true

# Optional: secure with basic auth
PROMETHEUS_METRICS_USER=prometheus
PROMETHEUS_METRICS_PASSWORD=metrics
```

See [Metrics Guide](../docs/METRICS_GUIDE.md) for Grafana dashboard setup.

## OIDC / SAML SSO

The backend supports external sign-in via OIDC and SAML.

### Core Environment Variables

```bash
SSO_ENABLED=true|false
SSO_AUTO_CREATE_USERS=true|false
SSO_SYNC_ROLES_ON_LOGIN=true|false
SSO_DEFAULT_ROLE=viewer
SSO_GROUP_ROLE_MAP={"GroupA":"admin","GroupB":"manager"}
```

### Provider Configuration

- `OIDC_PROVIDERS` - JSON object keyed by provider name
- `SAML_PROVIDERS` - JSON object keyed by provider name

See `infra/env/.env.example` for full Entra ID and Keycloak examples.

### API Endpoints

```
GET  /api/v1/auth/sso/providers
GET  /api/v1/auth/sso/oidc/authorize/{provider}?redirect_uri=...
POST /api/v1/auth/sso/oidc/exchange
POST /api/v1/auth/sso/saml/login
```

### Group-to-Role Mapping

1. Groups from OIDC/SAML claim are matched against `SSO_GROUP_ROLE_MAP`
2. Highest role wins (`admin > manager > viewer`)
3. If no mapping matches, `SSO_DEFAULT_ROLE` is applied

### Auto-Provisioning

- If `allow_auto_create` is `false` (or `SSO_AUTO_CREATE_USERS=false`), sign-in only works for pre-existing users
- Existing users can still authenticate and get role updates on login when `SSO_SYNC_ROLES_ON_LOGIN=true`

### Provider Setup Guides

- Entra ID: [SSO_ENTRA_ID_GUIDE.md](../docs/SSO_ENTRA_ID_GUIDE.md)
- Keycloak: [SSO_KEYCLOAK_GUIDE.md](../docs/SSO_KEYCLOAK_GUIDE.md)

## CI/CD

Backend tests run automatically via GitHub Actions:

- **backend-ci.yml**: pytest + Alembic migration validation
- Triggered on PRs to main

### Running CI Locally

```bash
# Run tests as CI would
docker compose -f infra/compose/docker-compose.yml run --rm backend pytest

# Validate migrations
docker compose -f infra/compose/docker-compose.yml run --rm backend alembic upgrade head
```

## Project Structure

```
backend/
├── app/
│   ├── api/                    # API routes
│   │   ├── router.py           # Central router (prefix=/api/v1)
│   │   └── v1/                 # Health, metrics
│   ├── domain/                 # 20+ domain modules
│   │   ├── auth/               # Authentication, users, SSO
│   │   ├── inventory/          # Products, devices, zones
│   │   ├── jobs/               # Jobs and requirements
│   │   ├── customers/          # Customers
│   │   ├── crew/               # Crew management
│   │   ├── finance/            # Financial transactions
│   │   ├── settings/           # App settings
│   │   └── ...
│   ├── db/                     # Models, session, seed
│   ├── services/               # Email, metrics, ProductionPlanner
│   ├── assistant/              # AI assistant
│   ├── config.py               # Pydantic Settings
│   └── main.py                 # FastAPI app entry
├── alembic/                    # 60+ migrations
├── scripts/                    # Seed, HireHop import
├── tests/                      # 156+ test functions
├── Dockerfile
└── pyproject.toml
```

## Related Documentation

- [API Overview](../docs/API_REFERENCE.md) - API structure (see `/docs` for full reference)
- [Database Schema](../docs/DATABASE_SCHEMA.md) - ERD and model details
- [Environment Variables](../docs/ENVIRONMENT_VARIABLES.md) - All config options
- [Development Guide](../docs/DEVELOPMENT_GUIDE.md) - Full dev workflow
