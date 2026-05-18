# Bootstrap and Repo Structure

## Suggested repository name
`eventcore-unified`

## Suggested tree

```text
eventcore-unified/
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
    BRAND_UI_SYSTEM.md
```

## 12-factor container notes
- Backend and frontend are separate images
- No local bind-mounted secrets in production
- Runtime config only via env vars/secrets
- One-off migration commands run as admin processes

## Initial milestones for first executable version
1. API health/auth scaffold
2. Quasar shell with login and dashboard
3. inventory + jobs read/write baseline
4. scan flow MVP for job and case
5. finance transaction schema and stats endpoints
