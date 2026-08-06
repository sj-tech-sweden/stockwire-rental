# Development Guide

> Last reviewed: 2026-08-06

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)
- Git

---

## Quick Start

### Docker Development (Recommended)

```bash
# Clone and setup
git clone <repo-url>
cd stockwire-rental
cp infra/env/.env.example infra/env/.env

# Start all services
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env up -d --build

# Run migrations
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend alembic upgrade head

# Seed demo data
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm backend python scripts/seed_demo.py
```

**Services:**
- Frontend: http://localhost:9000 (Quasar dev server with HMR)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python3.12 -m venv .venv312
source .venv312/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Setup database (requires running PostgreSQL)
export DATABASE_URL="postgresql+psycopg://stockwire_rental:stockwire_rental@localhost:5432/stockwire_rental"
alembic upgrade head

# Run demo seed
python scripts/seed_demo.py

# Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (PWA mode)
npm run dev
```

---

## Project Structure

```
stockwire-rental/
├── backend/                    # FastAPI backend
│   ├── app/                    # Application code
│   │   ├── api/                # API routes (v1)
│   │   ├── domain/             # Domain modules
│   │   ├── db/                 # Database models & session
│   │   ├── services/           # Shared services
│   │   ├── assistant/          # AI assistant
│   │   ├── config.py           # Settings (Pydantic)
│   │   └── main.py             # FastAPI app entry
│   ├── alembic/                # Database migrations
│   ├── scripts/                # Utility scripts
│   └── tests/                  # Backend tests
├── frontend/                   # Quasar frontend
│   ├── src/                    # Source code
│   │   ├── boot/               # Quasar boot files
│   │   ├── components/         # Vue components
│   │   ├── pages/              # Page components
│   │   ├── stores/             # Pinia stores
│   │   ├── services/           # API, offline, realtime
│   │   ├── i18n/               # Translations
│   │   └── utils/              # Utilities
│   └── tests/                  # Frontend tests
├── infra/                      # Infrastructure
│   ├── compose/                # Docker Compose files
│   └── env/                    # Environment files
├── docs/                       # Documentation
└── scripts/                    # Root scripts
```

---

## Backend Development

### Adding a New Domain Module

1. Create domain directory:

```bash
mkdir -p backend/app/domain/my_module
touch backend/app/domain/my_module/__init__.py
touch backend/app/domain/my_module/models.py
touch backend/app/domain/my_module/router.py
touch backend/app/domain/my_module/schemas.py
```

2. Define models in `models.py`:

```python
from sqlalchemy import Column, String
from app.db.base import Base

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
```

3. Create Pydantic schemas in `schemas.py`:

```python
from pydantic import BaseModel

class MyModelCreate(BaseModel):
    name: str

class MyModelRead(MyModelCreate):
    id: str
```

4. Add router in `router.py`:

```python
from fastapi import APIRouter, Depends
from app.db.session import get_db

router = APIRouter(prefix="/my-module", tags=["my-module"])

@router.get("/")
def list_items(db=Depends(get_db)):
    # implementation
    pass
```

5. Register router in `app/api/router.py`:

```python
from app.domain.my_module.router import router as my_module_router
api_router.include_router(my_module_router)
```

6. Add model to `app/db/models.py`:

```python
from app.domain.my_module.models import MyModel
```

7. Create migration:

```bash
cd backend
alembic revision --autogenerate -m "add my_module"
alembic upgrade head
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View current version
alembic current
```

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_api_crud.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app
```

---

## Frontend Development

### Adding a New Page

1. Create page component:

```bash
touch frontend/src/pages/MyPage.vue
```

2. Add route in `router/index.js`:

```javascript
{
  path: '/my-page',
  component: () => import('pages/MyPage.vue'),
  meta: { title: 'My Page' }
}
```

3. Add navigation item in `layouts/MainLayout.vue`:

```javascript
{
  label: t('app.nav.myPage'),
  icon: 'icon-name',
  to: '/my-page'
}
```

4. Add translations in `i18n/locales/en.js` and `sv.js`.

### Adding a New Component

1. Create component in `components/`:

```bash
touch frontend/src/components/MyComponent.vue
```

2. Follow existing patterns:
- Use `<script setup>` syntax
- Use Quasar components
- Use Pinia stores for data
- Use `$t()` for translations

### Adding a New Store

1. Create store file:

```bash
touch frontend/src/stores/myStore.js
```

2. Define store:

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useMyStore = defineStore('myStore', () => {
  const items = ref([])
  const loading = ref(false)

  async function fetchItems() {
    loading.value = true
    try {
      const { data } = await axios.get('/api/v1/my-module')
      items.value = data
    } finally {
      loading.value = false
    }
  }

  return { items, loading, fetchItems }
})
```

3. Register in `stores/index.js` if needed.

### Adding Translations

1. Add key to `i18n/locales/en.js`:

```javascript
export default {
  myModule: {
    title: 'My Module',
    actions: {
      create: 'Create Item'
    }
  }
}
```

2. Add corresponding key to `i18n/locales/sv.js`:

```javascript
export default {
  myModule: {
    title: 'Min modul',
    actions: {
      create: 'Skapa objekt'
    }
  }
}
```

3. Use in templates:

```vue
<template>
  <div>{{ $t('myModule.title') }}</div>
</template>
```

### Running Tests

```bash
cd frontend

# Unit tests
npm run test:smoke

# E2E tests
npm run test:e2e

# E2E with specific browser
npx playwright test --project=chromium
```

---

## API Development

### API Documentation

FastAPI auto-generates API docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Adding New Endpoints

1. Define route in domain router:

```python
@router.post("/items")
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    # implementation
    return created_item
```

2. Add response model:

```python
@router.post("/items", response_model=ItemRead)
def create_item(...):
```

3. Add to OpenAPI tags in `app/api/router.py`:

```python
api_router.include_router(
    my_router,
    tags=["my-module"],
    responses={404: {"description": "Not found"}}
)
```

---

## Debugging

### Backend

```bash
# View logs (Docker)
docker compose -f infra/compose/docker-compose.dev.yml logs -f backend

# Debug with VS Code
# Add to .vscode/launch.json:
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

### Frontend

```bash
# View logs (Docker)
docker compose -f infra/compose/docker-compose.dev.yml logs -f frontend

# Vue DevTools
# Install browser extension: https://devtools.vuejs.org/
```

### Database

```bash
# Connect to PostgreSQL
docker compose -f infra/compose/docker-compose.dev.yml exec postgres psql -U stockwire_rental -d stockwire_rental

# View tables
\dt

# View table structure
\d table_name
```

---

## Code Style

### Backend (Python)

- Follow PEP 8
- Use type hints
- Use Ruff for linting: `ruff check .`
- Use Black for formatting: `black .`

### Frontend (JavaScript/Vue)

- Use ESLint (Quasar default)
- Use `<script setup>` syntax
- Use Composition API
- Follow Quasar conventions

### Git

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Keep commits focused
- Reference issues in commit messages

---

## Common Tasks

### Reset Database

```bash
# Drop and recreate
docker compose -f infra/compose/docker-compose.dev.yml exec postgres psql -U stockwire_rental -c "DROP DATABASE stockwire_rental;"
docker compose -f infra/compose/docker-compose.dev.yml exec postgres psql -U stockwire_rental -c "CREATE DATABASE stockwire_rental;"

# Re-run migrations
docker compose -f infra/compose/docker-compose.dev.yml run --rm backend alembic upgrade head

# Re-seed
docker compose -f infra/compose/docker-compose.dev.yml run --rm backend python scripts/seed_demo.py
```

### Regenerate OpenAPI Spec

```bash
cd backend
python -c "from app.main import app; import json; json.dump(app.openapi(), open('openapi.json', 'w'), indent=2)"
```

### Update Frontend Dependencies

```bash
cd frontend
npm update
npm audit fix
```

---

## CI/CD

### GitHub Actions

- `ci.yml` - Frontend tests + build + Playwright E2E
- `backend-ci.yml` - Backend pytest + Alembic migration validation

### Running CI Locally

```bash
# Frontend CI
docker compose -f infra/compose/docker-compose.dev.yml run --rm frontend npm run test:smoke
docker compose -f infra/compose/docker-compose.dev.yml run --rm frontend npm run build

# Backend CI
docker compose -f infra/compose/docker-compose.yml run --rm backend pytest
```

---

## Getting Help

- Check existing documentation in `docs/`
- Review code comments
- Look at existing implementations for patterns
- Check GitHub issues for known problems
