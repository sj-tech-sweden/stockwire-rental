# Stockwire Rental

Rental and warehouse platform in one application with:

- FastAPI backend
- Quasar frontend
- Separate containers
- 12-factor operational model

## Current baseline status (2026-05-22)

Already delivered in baseline:

- Eventory integration baseline with multi-instance configuration and default endpoint handling.
- Storage abstraction with interchangeable `local` and `s3` backends.
- Attachment support for company, jobs, products, devices, and maintenance entities.
- Offline queue baseline (flush/retry/blocked workflows and conflict policy visibility).
- SSO baseline (OIDC/SAML provider configuration and role mapping flows).
- Ongoing i18n expansion across inventory/settings surfaces.

## Why this repo exists

This repository consolidates the current RentalCore and WarehouseCore capabilities into one product and one API surface while preserving modular domain boundaries.

Execution is prioritized from WarehouseCore open issues while keeping a consistent branded UI system (green cable motif, dark canvas, high-contrast utility UI).

## Repository goals

- Single source of truth for jobs, inventory, scans, finance, and analytics
- Mobile-first operational workflows for scanning and picking
- Pluggable integrations (Eventory multi-instance, S3-compatible storage, SSO)
- Strict 12-factor architecture for cloud-native deployments

## What to read first

- New contributors: [Bootstrap & Repo Structure](docs/BOOTSTRAP.md)
- Product/delivery status: [Issue-Driven Roadmap](docs/ROADMAP_FROM_ISSUES.md)
- Architecture/runtime model: [12-Factor Architecture](docs/ARCHITECTURE_12FACTOR.md)
- Storage choice and migration: [Storage and File Upload Guide](docs/STORAGE_FILES_GUIDE.md)

## Docs index

- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [12-Factor Architecture](docs/ARCHITECTURE_12FACTOR.md)
- [Issue-Driven Roadmap](docs/ROADMAP_FROM_ISSUES.md)
- [Brand & UI System for Quasar](docs/BRAND_UI_SYSTEM.md)
- [Bootstrap & Repo Structure](docs/BOOTSTRAP.md)
- [Entra ID SSO Guide](docs/SSO_ENTRA_ID_GUIDE.md)
- [Keycloak SSO Guide](docs/SSO_KEYCLOAK_GUIDE.md)
- [Storage and File Upload Guide](docs/STORAGE_FILES_GUIDE.md)
- [Test Coverage Matrix](docs/TEST_COVERAGE_MATRIX.md)

## Proposed stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Redis, Celery/Arq
- Frontend: Quasar (Vue 3 + Vite + TypeScript + Pinia)
- Data: PostgreSQL 16+, Redis
- Messaging: MQTT bridge + internal event bus abstraction
- Observability: OpenTelemetry, Prometheus metrics, structured JSON logging

## Delivery approach

1. Harden mobile scanning and overflow-safe UI workflows
2. Complete zone/defect/admin UX refactors from active backlog
3. Expand docs + quality gates per feature PR
4. Deepen offline conflict resolution and live-update reliability

## Quick start (containers)

```bash
cp infra/env/.env.example infra/env/.env
docker compose -f infra/compose/docker-compose.yml --env-file infra/env/.env up -d --build
```

Services:

- Backend API: <http://localhost:8000>
- Frontend (production-style nginx build): <http://localhost:9000>

## Storage backend quick guidance

- Use `local` for single-node local development with persistent mounted volumes.
- Use `s3` for multi-node environments and production durability/operations.
- See [Storage and File Upload Guide](docs/STORAGE_FILES_GUIDE.md) for env variables and migration steps.

## Eventory integration quick guidance

- Baseline supports multi-instance configurations and a default API endpoint.
- Keep integration metadata explicit to avoid UI ambiguity between manual and synced records.
- Operational details belong in integration settings and corresponding deployment env vars.

## Local dev workflow

Use `infra/compose/docker-compose.dev.yml` when you want the Quasar dev server locally, or `infra/compose/docker-compose.yml` when you want to verify the production-style nginx frontend container.

```bash
cp infra/env/.env.example infra/env/.env
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env up -d --build
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend alembic upgrade head
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend python scripts/seed_demo.py
```

## Tests

Backend API integration tests:

```bash
docker compose -f infra/compose/docker-compose.yml --env-file infra/env/.env run --rm backend pytest
```

Frontend smoke tests:

```bash
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm frontend npm run test:smoke
```

## Milestone issue automation

Create first milestone issues in a GitHub repo:

```bash
./scripts/create_m1_issues.sh jorblad/stockwire-rental
```
