# 12-Factor Architecture (FastAPI + Quasar)

Last reviewed: 2026-05-22

This architecture guide describes the target 12-factor shape and highlights what is already in baseline delivery.

## Current status snapshot

- Integrations baseline is live for Eventory (multi-instance + default endpoint behavior).
- Storage abstraction is live with interchangeable local disk and S3-compatible object storage backends.
- Offline queue baseline exists (flush/retry/blocked) with conflict policy visibility in UI.
- Attachment capabilities are available for company, jobs, products, devices, and maintenance records.

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
- Valkey/Redis
- MQTT broker
- S3-compatible object storage or local persistent volume (by environment policy)
- OIDC provider (optional)

## 5. Build, release, run

- Build: immutable Docker images for backend/frontend
- Release: image + env var bundle + migration version
- Run: stateless processes; persistent file data belongs in configured storage backends, not ephemeral container filesystems

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
- Keep behavior parity while allowing environment-specific storage backend choice (`local` for simple single-node dev, `s3` for multi-node/prod)

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

## Integration implementation notes

- Eventory synchronization should rely on explicit external references and integration metadata, not UI-only heuristics.
- Storage provider selection is a runtime config concern; model-level file references stay provider-agnostic.
- Offline synchronization must preserve idempotency keys for replay-safe retries.

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

## Related docs

- `docs/STORAGE_FILES_GUIDE.md` for storage backend selection and migration steps.
- `docs/ROADMAP_FROM_ISSUES.md` for active priorities and delivered items.
- `docs/IMPLEMENTATION_PLAN.md` for phased execution plan and quality gates.
