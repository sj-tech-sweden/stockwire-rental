# Stockwire Rental

Rental and warehouse platform in one application with:
- FastAPI backend
- Quasar frontend
- Separate containers
- 12-factor operational model

## Why this repo exists
This repository consolidates the current RentalCore and WarehouseCore capabilities into one product and one API surface while preserving modular domain boundaries.

It is planned specifically around your open WarehouseCore issues and a branded UI system inspired by your attached logo (green cable motif, dark canvas, high-contrast utility UI).

## Repository goals
- Single source of truth for jobs, inventory, scans, finance, and analytics
- Mobile-first operational workflows for scanning and picking
- Pluggable integrations (Eventory multi-instance, S3-compatible storage, SSO)
- Strict 12-factor architecture for cloud-native deployments

## Docs index
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [12-Factor Architecture](docs/ARCHITECTURE_12FACTOR.md)
- [Issue-Driven Roadmap](docs/ROADMAP_FROM_ISSUES.md)
- [Brand & UI System for Quasar](docs/BRAND_UI_SYSTEM.md)
- [Bootstrap & Repo Structure](docs/BOOTSTRAP.md)

## Proposed stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Redis, Celery/Arq
- Frontend: Quasar (Vue 3 + Vite + TypeScript + Pinia)
- Data: PostgreSQL 16+, Redis
- Messaging: MQTT bridge + internal event bus abstraction
- Observability: OpenTelemetry, Prometheus metrics, structured JSON logging

## Delivery approach
1. Foundation + auth + core inventory/job flows
2. Mobile scanning and UX fixes
3. Integrations (SSO, Eventory multi-instance, storage abstraction)
4. Offline-first sync and advanced admin UX

## Quick start (containers)

```bash
cp infra/env/.env.example infra/env/.env
docker compose -f infra/compose/docker-compose.yml --env-file infra/env/.env up -d --build
```

Services:
- Backend API: http://localhost:8000
- Frontend (Quasar dev): http://localhost:9000

## Milestone issue automation

Create first milestone issues in a GitHub repo:

```bash
./scripts/create_m1_issues.sh jorblad/stockwire-rental
```
