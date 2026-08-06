# Bootstrap and Repo Structure

> Last reviewed: 2026-08-06

This document serves two purposes:

- Quick orientation for a clean bootstrap
- Current-state snapshot so new contributors do not repeat already completed baseline work

## Suggested repository name

`stockwire-rental`

## Repository Structure

```text
stockwire-rental/
├── backend/
│   ├── app/
│   │   ├── api/                    # API routes (v1)
│   │   │   ├── router.py           # Central API router
│   │   │   └── v1/                 # Health, metrics endpoints
│   │   ├── domain/                 # Domain modules (20+)
│   │   │   ├── auth/               # Authentication, users, SSO
│   │   │   ├── inventory/          # Products, devices, zones, maintenance
│   │   │   ├── jobs/               # Jobs and requirements
│   │   │   ├── customers/          # Customers
│   │   │   ├── venues/             # Venues
│   │   │   ├── projects/           # Projects
│   │   │   ├── crew/               # Crew management
│   │   │   ├── finance/            # Financial transactions
│   │   │   ├── settings/           # App settings
│   │   │   ├── storage/            # File storage
│   │   │   ├── notifications/      # Push/email notifications
│   │   │   ├── calendar_feeds/     # ICS calendar feeds
│   │   │   ├── custom_fields/      # Custom field system
│   │   │   ├── route_planner/      # Route planning
│   │   │   ├── warehouse_leds/     # LED controller integration
│   │   │   ├── integrations/       # Twenty CRM, etc.
│   │   │   ├── realtime/           # WebSocket hub
│   │   │   ├── audit/              # Activity logs
│   │   │   └── led/                # (placeholder)
│   │   ├── db/                     # Models, session, seed
│   │   ├── services/               # Email, metrics, ProductionPlanner
│   │   ├── assistant/              # AI assistant (LLM)
│   │   ├── config.py               # Pydantic Settings
│   │   └── main.py                 # FastAPI app entry
│   ├── alembic/                    # 60+ migrations
│   ├── scripts/                    # Seed, HireHop import
│   ├── tests/                      # 156+ test functions
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── boot/                   # 7 boot files (axios, i18n, theme, etc.)
│   │   ├── components/             # 66 Vue components
│   │   ├── pages/                  # 26 page components
│   │   ├── stores/                 # 16 Pinia stores
│   │   ├── services/               # API, offline (Orbit.js), realtime
│   │   ├── i18n/                   # English + Swedish translations
│   │   ├── layouts/                # Auth + Main layouts
│   │   ├── router/                 # Vue Router config
│   │   ├── composables/            # Reusable Vue logic
│   │   ├── constants/              # Static data
│   │   ├── css/                    # Global styles
│   │   └── utils/                  # Utility functions
│   ├── tests/                      # Unit (Vitest) + E2E (Playwright)
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── compose/                    # Docker Compose files
│   │   ├── docker-compose.yml      # Production
│   │   └── docker-compose.dev.yml  # Development
│   └── env/
│       └── .env.example            # Environment template
├── docs/                           # Documentation
├── scripts/                        # Root scripts (milestone issues)
└── .github/                        # CI/CD workflows
    ├── workflows/
    └── pull_request_template.md
```

## 12-Factor Container Notes

- Backend and frontend are separate Docker images
- No local bind-mounted secrets in production
- Runtime configuration via environment variables only
- One-off migration commands run as admin processes
- Structured JSON logging with correlation IDs
- Prometheus metrics endpoint available

## Current Baseline Already Delivered

- **Eventory Integration** - Multi-instance configuration, default endpoint handling, auto-scan
- **Storage Abstraction** - Interchangeable `local` and `s3` backends for attachments
- **Attachment Flows** - Wired for company, jobs, products, devices, maintenance, customers, venues
- **Offline Queue** - Retry/flush/blocked states, conflict visibility, IndexedDB sync
- **SSO Baseline** - OIDC/SAML provider configuration, role mapping, auto-provisioning
- **i18n Expansion** - English + Swedish translations across inventory/settings surfaces
- **Crew Management** - Roles, skills, certifications, job assignments
- **Route Planning** - Vehicle management, multi-vehicle routes, Google Maps export
- **Warehouse LEDs** - MQTT-based LED controller integration, bin highlighting
- **Calendar Feeds** - ICS subscriptions for jobs and maintenance
- **Custom Fields** - Dynamic fields for products, jobs, customers, venues
- **Notification System** - Web push + email dispatch with templates
- **Twenty CRM Integration** - Bidirectional sync with Twenty CRM
- **ProductionPlanner Integration** - Job/project sync
- **AI Assistant** - LLM-powered chat with tool execution
- **Metrics** - Prometheus metrics, Grafana dashboards
- **Realtime** - WebSocket hub for live updates

## Next Milestones (Remaining High-Value Work)

1. Mobile-first scan and pick flows with viewport-safe behavior and reduced horizontal overflow
2. Zone editing and bulk subzone workflows with stronger hierarchy validation
3. Defect report editing with timeline comments and complete audit entries
4. Light mode + contrast hardening and docs update automation in each feature PR
5. Deeper offline conflict resolution UX and live update convergence

## Quick Start (Docker)

```bash
# Clone repository
git clone <repo-url>
cd stockwire-rental

# Setup environment
cp infra/env/.env.example infra/env/.env

# Start development
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env up -d --build

# Run migrations
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend alembic upgrade head

# Seed demo data
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend python scripts/seed_demo.py
```

**Services:**
- Frontend: http://localhost:9000 (Quasar dev server)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Related Documentation

- **New Contributors**: [Development Guide](DEVELOPMENT_GUIDE.md)
- **Architecture**: [12-Factor Architecture](ARCHITECTURE_12FACTOR.md)
- **API Overview**: [API Overview](API_REFERENCE.md) (also see auto-generated docs at `/docs`)
- **Frontend**: [Frontend Architecture](FRONTEND_ARCHITECTURE.md)
- **Database**: [Database Schema](DATABASE_SCHEMA.md)
- **Environment**: [Environment Variables](ENVIRONMENT_VARIABLES.md)
- **Storage**: [Storage Files Guide](STORAGE_FILES_GUIDE.md)
- **Testing**: [Testing Guide](TESTING_GUIDE.md)
- **Roadmap**: [Issue-Driven Roadmap](ROADMAP_FROM_ISSUES.md)
- **Brand/UI**: [Brand UI System](BRAND_UI_SYSTEM.md)
- **SSO**: [Entra ID Guide](SSO_ENTRA_ID_GUIDE.md), [Keycloak Guide](SSO_KEYCLOAK_GUIDE.md)
- **Metrics**: [Metrics Guide](METRICS_GUIDE.md)
- **Route Planning**: [Route Planner](ROUTE_PLANNER.md)
- **Crew**: [Crew Management](CREW_MANAGEMENT.md)
- **LEDs**: [Warehouse LEDs](WAREHOUSE_LEDS.md)
- **Calendar**: [Calendar Feeds](CALENDAR_FEEDS.md)
- **Custom Fields**: [Custom Fields](CUSTOM_FIELDS.md)
- **Notifications**: [Notifications](NOTIFICATIONS.md)
- **i18n**: [i18n Guide](I18N_GUIDE.md)
