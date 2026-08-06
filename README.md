# Stockwire Rental

Rental and warehouse platform in one application with:

- FastAPI backend
- Quasar frontend (PWA with offline-first support)
- Separate containers
- 12-factor operational model

## Current Baseline Status (2026-08-06)

Already delivered in baseline:

- **Eventory Integration** - Multi-instance configuration, default endpoint handling, auto-scan
- **Storage Abstraction** - Interchangeable `local` and `s3` backends for attachments
- **Attachment Flows** - Wired for company, jobs, products, devices, maintenance, customers, venues
- **Offline Queue** - Retry/flush/blocked states, conflict visibility, IndexedDB sync
- **SSO Baseline** - OIDC/SAML provider configuration, role mapping, auto-provisioning
- **i18n** - English + Swedish translations across inventory/settings surfaces
- **Crew Management** - Roles, skills, certifications, job assignments
- **Route Planning** - Vehicle management, multi-vehicle routes, Google Maps export
- **Warehouse LEDs** - MQTT-based LED controller integration, bin highlighting
- **Calendar Feeds** - ICS subscriptions for jobs and maintenance
- **Custom Fields** - Dynamic fields for products, jobs, customers, venues
- **Notification System** - Web push + email dispatch with templates
- **Twenty CRM Integration** - Bidirectional sync
- **ProductionPlanner Integration** - Job/project sync
- **AI Assistant** - LLM-powered chat with tool execution
- **Metrics** - Prometheus metrics, Grafana dashboards
- **Realtime** - WebSocket hub for live updates

## Why This Repo Exists

This repository consolidates the current RentalCore and WarehouseCore capabilities into one product and one API surface while preserving modular domain boundaries.

Execution is prioritized from WarehouseCore open issues while keeping a consistent branded UI system (green cable motif, dark canvas, high-contrast utility UI).

## Repository Goals

- Single source of truth for jobs, inventory, scans, finance, and analytics
- Mobile-first operational workflows for scanning and picking
- Pluggable integrations (Eventory multi-instance, S3-compatible storage, SSO)
- Strict 12-factor architecture for cloud-native deployments

## What to Read First

- **New Contributors**: [Bootstrap & Repo Structure](docs/BOOTSTRAP.md)
- **Development Setup**: [Development Guide](docs/DEVELOPMENT_GUIDE.md)
- **API Overview**: [API Overview](docs/API_REFERENCE.md) (also see auto-generated docs at `/docs`)
- **Architecture**: [12-Factor Architecture](docs/ARCHITECTURE_12FACTOR.md)
- **Frontend**: [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md)

## Documentation Index

### Core Documentation

| Document | Description |
|----------|-------------|
| [Bootstrap & Repo Structure](docs/BOOTSTRAP.md) | Repository orientation for new contributors |
| [Development Guide](docs/DEVELOPMENT_GUIDE.md) | Local dev, testing, debugging workflows |
| [API Overview](docs/API_REFERENCE.md) | API structure and patterns (see `/docs` for full reference) |
| [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md) | Frontend structure, stores, components |
| [Database Schema](docs/DATABASE_SCHEMA.md) | ERD overview, model relationships, migrations |
| [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) | Complete env var reference |

### Architecture & Planning

| Document | Description |
|----------|-------------|
| [12-Factor Architecture](docs/ARCHITECTURE_12FACTOR.md) | Architecture decisions and runtime model |
| [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) | Phased implementation approach |
| [Issue-Driven Roadmap](docs/ROADMAP_FROM_ISSUES.md) | Backlog priorities and delivery status |
| [Test Coverage Matrix](docs/TEST_COVERAGE_MATRIX.md) | Automated test coverage mapping |

### UI & Brand

| Document | Description |
|----------|-------------|
| [Brand & UI System](docs/BRAND_UI_SYSTEM.md) | Design tokens, colors, typography |
| [i18n Guide](docs/I18N_GUIDE.md) | Internationalization for developers |

### Feature Guides

| Document | Description |
|----------|-------------|
| [Route Planner](docs/ROUTE_PLANNER.md) | Route planning and vehicle management |
| [Crew Management](docs/CREW_MANAGEMENT.md) | Crew roles, skills, certifications |
| [Warehouse LEDs](docs/WAREHOUSE_LEDS.md) | LED controller integration |
| [Calendar Feeds](docs/CALENDAR_FEEDS.md) | ICS calendar subscriptions |
| [Custom Fields](docs/CUSTOM_FIELDS.md) | Dynamic field system |
| [Notifications](docs/NOTIFICATIONS.md) | Push and email notifications |

### Integration Guides

| Document | Description |
|----------|-------------|
| [Storage & Files](docs/STORAGE_FILES_GUIDE.md) | Local vs S3 storage, file uploads |
| [Entra ID SSO](docs/SSO_ENTRA_ID_GUIDE.md) | Microsoft Entra ID integration |
| [Keycloak SSO](docs/SSO_KEYCLOAK_GUIDE.md) | Keycloak integration |
| [Metrics Guide](docs/METRICS_GUIDE.md) | Prometheus + Grafana monitoring |

### Operations

| Document | Description |
|----------|-------------|
| [Release & Secrets](docs/RELEASE_AND_SECRETS.md) | Release workflow, required secrets |
| [Playwright Artifacts](docs/PLAYWRIGHT_ARTIFACTS.md) | E2E test artifact management |
| [Testing Guide](docs/TESTING_GUIDE.md) | Testing strategy and best practices |
| [Milestone 1 Issues](docs/MILESTONE_1_ISSUES.md) | MVP issue drafts |

## Proposed Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Redis
- **Frontend**: Quasar (Vue 3 + Vite + Pinia), Orbit.js (offline-first)
- **Data**: PostgreSQL 16+, Redis
- **Messaging**: MQTT bridge + internal event bus abstraction
- **Observability**: Prometheus metrics, structured JSON logging

## Quick Start (Docker)

```bash
cp infra/env/.env.example infra/env/.env
docker compose -f infra/compose/docker-compose.yml --env-file infra/env/.env up -d --build
```

**Services:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:9000

## Local Dev Workflow

Use `infra/compose/docker-compose.dev.yml` for Quasar dev server with HMR:

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

## Milestone Issue Automation

Create first milestone issues in a GitHub repo:

```bash
./scripts/create_m1_issues.sh jorblad/stockwire-rental
```
