# Bootstrap and Repo Structure

This document now serves two purposes:

- quick orientation for a clean bootstrap,
- current-state snapshot so new contributors do not repeat already completed baseline work.

## Suggested repository name

`stockwire-rental`

## Suggested tree

```text
stockwire-rental/
  backend/
    app/
      api/
      domain/
      infra/
      main.py
    alembic/
    tests/
    Dockerfile
    pyproject.toml
  frontend/
    src/
    public/
    Dockerfile
    package.json
  infra/
    compose/
      docker-compose.yml
    env/
      .env.example
  docs/
    IMPLEMENTATION_PLAN.md
    ARCHITECTURE_12FACTOR.md
    ROADMAP_FROM_ISSUES.md
    STORAGE_FILES_GUIDE.md
    BRAND_UI_SYSTEM.md
```

## 12-factor container notes

- Backend and frontend are separate images
- No local bind-mounted secrets in production
- Runtime config only via env vars/secrets
- One-off migration commands run as admin processes

## Current baseline already delivered

- Eventory integration baseline with support for per-instance configuration and default endpoint handling.
- Storage abstraction with interchangeable `local` and `s3` backends for attachments.
- Attachment flows wired for company, jobs, products, devices, and maintenance entities.
- Offline queue baseline including retry/flush/blocked states and conflict visibility.
- SSO baseline (OIDC/SAML provider configuration and role-mapping paths).
- Broad i18n expansion in key inventory/settings workflows.

## Next milestones (remaining high-value work)

1. Mobile-first scan and pick flows with viewport-safe behavior and reduced horizontal overflow.
2. Zone editing and bulk subzone workflows with stronger hierarchy validation.
3. Defect report editing with timeline comments and complete audit entries.
4. Light mode + contrast hardening and docs update automation in each feature PR.
5. Deeper offline conflict resolution UX and live update convergence.

## Related docs

- `docs/STORAGE_FILES_GUIDE.md` for local disk vs S3 decision and migration guidance.
- `docs/ROADMAP_FROM_ISSUES.md` for backlog priorities and delivery status.
- `docs/IMPLEMENTATION_PLAN.md` for phase sequencing and quality gates.
