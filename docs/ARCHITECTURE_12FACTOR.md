# 12-Factor Architecture (FastAPI + Quasar)

## 1. Codebase
- One repo: Stockwire Rental
- Modular monolith approach first: domain modules with clean boundaries
- Optional future extraction to services via event contracts

## 2. Dependencies
- Python and Node dependencies declared in lockfiles
- No global runtime assumptions inside containers

## 3. Config
- All environment-specific values via env vars
- No hardcoded secrets, URLs, feature flags, or tenant values
- Secret loading via runtime secret manager in production

## 4. Backing services
Treat all backing services as attached resources:
- PostgreSQL
- Redis
- MQTT broker
- S3-compatible object storage
- OIDC provider (optional)

## 5. Build, release, run
- Build: immutable Docker images for backend/frontend
- Release: image + env var bundle + migration version
- Run: stateless processes, no mutable container filesystem dependency

## 6. Processes
- API container stateless
- Worker container for async jobs
- Scheduler container for periodic jobs

## 7. Port binding
- FastAPI serves HTTP on internal port
- Quasar served as static app from nginx container or Quasar SSR container

## 8. Concurrency
Scale by process type:
- api replicas
- worker replicas
- websocket replica group (if enabled)

## 9. Disposability
- Fast startup with readiness checks
- Graceful shutdown hooks for worker drain and websocket disconnects

## 10. Dev/prod parity
- Same Dockerized topology in local/stage/prod
- Local overrides only in env files, not code

## 11. Logs
- Structured logs to stdout
- Correlation IDs propagated from frontend to backend and workers

## 12. Admin processes
- One-off tasks as ephemeral commands:
  - db migrations
  - backfill scripts
  - issue repair scripts

## Domain modules (backend)
- auth: sessions, passkeys, OIDC/SAML bridge, RBAC
- inventory: products, devices, cases, zones, movements
- jobs: requirements, picks, scan in/out, job lifecycle
- defects: reports, comments, edit history
- finance: transactions, invoices, overdue tracking, reports
- integrations: Eventory, storage providers, webhooks
- analytics: KPI and trend aggregates

## Suggested service containers
- api: FastAPI + Uvicorn
- worker: async task processor
- scheduler: periodic tasks
- frontend: Quasar build and runtime
- postgres
- redis
- mqtt

## Suggested env var groups
- APP_: runtime identity, URLs, feature flags
- DB_: database settings
- REDIS_: cache/queue settings
- AUTH_: session/OIDC/SAML settings
- STORAGE_: S3/MinIO/Cloud provider settings
- EVENTORY_: default endpoint and per-vendor configs
- OBS_: tracing/metrics/logging controls
