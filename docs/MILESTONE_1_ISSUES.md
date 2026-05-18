# Milestone 1 Backlog (GitHub Issues)

These issues cover the first executable milestone: foundation + core operational UX blockers.

## Issue drafts

1. Foundation: FastAPI service skeleton and Quasar shell
- Scope: establish app modules, auth guard rails, shared layout, base observability
- Acceptance:
  - health/readiness endpoints
  - Quasar shell with routing
  - docker compose up works end-to-end

2. Mobile scanning MVP for jobs and cases
- Scope: scan-first flow for job outtake/intake and case scan expansion
- Covers: warehousecore #105, #112
- Acceptance:
  - case scan includes child devices
  - strict check-in mode requires per-device verify
  - mobile flow has scanner action pinned

3. Fix viewport and scrolling consistency across core pages
- Scope: layout shell overflow policy + page wrappers
- Covers: warehousecore #114
- Acceptance:
  - no unreachable content at 360x800 and 390x844

4. Device job info panel with enriched context
- Scope: improve device popover when assigned to a job
- Covers: warehousecore #118
- Acceptance:
  - show job code, customer, date range, status, remaining picks

5. Financial transaction domain baseline
- Scope: create robust schema and report-safe endpoints
- Acceptance:
  - transaction_date, due_date, status, type fields present
  - overdue and revenue reports return without SQL errors

6. Zone editing and bulk subzone management (phase-in)
- Scope: initial backend contracts and frontend placeholders
- Covers: warehousecore #117
- Acceptance:
  - API stubs and UI routes in place for phase 2 completion

7. Defect report edit + comments timeline foundations
- Scope: data model and API contracts
- Covers: warehousecore #115
- Acceptance:
  - defect_comments table and CRUD endpoints scaffolded

## Recommended labels
- `milestone:1`
- `area:backend`
- `area:frontend`
- `area:infra`
- `priority:p0`
- `priority:p1`

## Suggested milestone name
`M1 - Unified Core MVP`
