# Implementation Plan: Stockwire Rental

## Target outcome
One application replacing split RentalCore/WarehouseCore responsibilities with:
- FastAPI backend container
- Quasar frontend container
- 12-factor deployment model
- Issue-driven roadmap from existing WarehouseCore pain points

## Phase 0: Discovery and contracts (1-2 weeks)
- Finalize domain model merge (jobs, inventory, devices, cases, zones, finance)
- Define OpenAPI v1 baseline
- Create event contracts for scan and inventory movement
- Confirm grafisk profil exact tokens (colors, fonts)

Deliverables:
- ERD v1
- OpenAPI v1
- Brand token JSON

## Phase 1: Foundation platform (2-3 weeks)
- FastAPI service skeleton with module boundaries
- Quasar app shell with auth, routing, layout primitives
- RBAC, session auth, API key support, audit trail core
- PostgreSQL + Alembic + seed scripts
- CI/CD with lint/test/build/image scan

Deliverables:
- Running dev stack in docker compose
- Health/readiness checks
- CI green baseline

## Phase 2: Core operations (3-4 weeks)
- Jobs CRUD + requirements + statuses
- Inventory/products/devices/cases/zones core
- Scan in/out foundation with movement logs
- Financial transaction module with reporting-safe schema

Issues covered:
- #118, #114, #112, #105 (first pass)

## Phase 3: Workflow UX improvements (3 weeks)
- Inline requirement editing with search/tree (#111)
- Zone edit + bulk subzones (#117)
- Defect report edit + comments timeline (#115)
- Admin navigation redesign (#104)
- Light/auto theme (#108)

## Phase 4: Integrations and enterprise features (3-4 weeks)
- SSO OIDC baseline + mapping (#110)
- Eventory multi-instance and default endpoint (#109)
- Storage abstraction replacing Nextcloud dependency (#101)
- Rental equipment scan lifecycle (#106)

## Phase 5: Offline and reliability (4+ weeks)
- Offline action queue and sync engine (#103)
- websocket live updates for online mode
- conflict resolution strategy and user prompts

## Quality gates per phase
- Unit tests (backend/frontend)
- API contract tests
- Migration validation tests
- Mobile viewport acceptance checks
- Security checks (dependency, secrets, auth policy)
- Docs updated (#102)

## Team topology
- Backend lead (FastAPI, DB, auth)
- Frontend lead (Quasar UX/mobile)
- Platform engineer (CI/CD, observability, infra)
- Product/ops tester (scan flow and warehouse acceptance)

## Risks and mitigations
- Scope risk: keep modular monolith boundaries and phased backlog
- UX regressions on mobile: enforce viewport QA and real device checks
- Integration drift: adapter interfaces + contract tests
- Branding mismatch: lock token source from grafisk profile before UI freeze
