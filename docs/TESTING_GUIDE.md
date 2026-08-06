# Testing Guide

> Last reviewed: 2026-08-06

## Overview

Stockwire Rental uses a multi-layered testing strategy:

- **Backend Unit/Integration Tests** - pytest
- **Frontend Unit Tests** - Vitest
- **E2E Tests** - Playwright

---

## Backend Tests

### Location

```
backend/tests/
├── conftest.py                    # Fixtures
├── test_api_crud.py              # CRUD tests (~50 tests)
├── test_assistant.py             # AI assistant tests
├── test_route_planner.py         # Route planner tests
├── test_notifications.py         # Notification tests
├── test_health.py                # Health endpoint
├── test_modules.py               # Bootstrap status
├── test_twenty_sync.py           # Twenty CRM sync
├── test_productionplanner_service.py  # ProductionPlanner
├── test_eventory_auto_scan.py    # Eventory scanning
├── test_eventory_token.py        # Eventory token/SSRF
├── test_auth_password_hashing.py # Password hashing
└── test_auth_api_key_hashing.py  # API key hashing
```

### Running Tests

```bash
cd backend

# All tests
pytest

# Specific file
pytest tests/test_api_crud.py

# With verbose output
pytest -v

# With coverage
pytest --cov=app

# Stop on first failure
pytest -x
```

### Test Structure

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# SQLite in-memory for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### Writing Tests

```python
def test_create_product(client, db_session):
    response = client.post(
        "/api/v1/inventory/products",
        json={
            "name": "Test Product",
            "sku": "TEST-001",
            "category_id": "uuid-here"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert "id" in data
```

### Test Coverage

| Area | Coverage | Notes |
|------|----------|-------|
| Auth | High | Login, SSO, API keys |
| Inventory | High | CRUD, bulk ops, scan |
| Jobs | High | CRUD, requirements |
| Finance | Medium | Transactions |
| Route Planner | Medium | CRUD, suggestions |
| Crew | Low | Basic CRUD only |
| Warehouse LEDs | Low | Basic tests |
| Calendar Feeds | None | Not tested |
| Notifications | Low | Basic tests |

---

## Frontend Tests

### Location

```
frontend/tests/
├── setup/
│   └── indexeddb.setup.js    # fake-indexeddb setup
├── router.smoke.test.js      # Router smoke tests
├── stores.smoke.test.js      # Stores smoke tests
├── unit/                     # 22 unit test files
│   ├── currencies.test.js
│   ├── dashboard-links.test.js
│   ├── export-data.test.js
│   └── ...
└── e2e/                      # 5 E2E test files
    ├── helpers/
    │   └── session.ts
    ├── finance-transaction-flow.spec.ts
    ├── inventory-settings-custom-fields.spec.ts
    ├── labels-template-flow.spec.ts
    ├── scan-device-lifecycle.spec.ts
    └── setup-login-create-user.spec.ts
```

### Running Tests

```bash
cd frontend

# Unit tests (Vitest)
npm run test:smoke

# E2E tests (Playwright)
npm run test:e2e

# E2E with specific browser
npx playwright test --project=chromium
```

### Unit Test Structure

```javascript
// tests/unit/currencies.test.js
import { describe, it, expect } from 'vitest'
import { formatCurrency } from '@/utils/currencies'

describe('formatCurrency', () => {
  it('formats USD correctly', () => {
    expect(formatCurrency(1234.56, 'USD')).toBe('$1,234.56')
  })
  
  it('formats EUR correctly', () => {
    expect(formatCurrency(1234.56, 'EUR')).toBe('€1,234.56')
  })
})
```

### Writing Unit Tests

```javascript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  it('renders correctly', () => {
    const wrapper = mount(MyComponent, {
      props: { title: 'Test' }
    })
    expect(wrapper.text()).toContain('Test')
  })
  
  it('emits event on click', async () => {
    const wrapper = mount(MyComponent)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
```

### Test Coverage

| Area | Coverage | Notes |
|------|----------|-------|
| Utils | High | Most utilities tested |
| Stores | Medium | Smoke tests only |
| Components | Low | Limited component tests |
| Router | Low | Smoke tests only |
| Pages | None | No page tests |

---

## E2E Tests (Playwright)

### Configuration

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180000,
  workers: 1,
  use: {
    baseURL: 'http://localhost:9000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry'
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } }
  ]
})
```

### Running E2E Tests

```bash
cd frontend

# All tests
npm run test:e2e

# Specific file
npx playwright test tests/e2e/finance-transaction-flow.spec.ts

# With UI
npx playwright test --ui

# Debug mode
npx playwright test --debug
```

### Writing E2E Tests

```typescript
// tests/e2e/setup-login-create-user.spec.ts
import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/session'

test('setup and create user', async ({ page }) => {
  // Login
  await loginAsAdmin(page)
  
  // Navigate to users
  await page.click('text=Settings')
  await page.click('text=Users')
  
  // Create user
  await page.click('text=Add User')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('text=Save')
  
  // Verify
  await expect(page.locator('text=test@example.com')).toBeVisible()
})
```

### E2E Test Helpers

```typescript
// tests/e2e/helpers/session.ts
import { Page } from '@playwright/test'

export async function loginAsAdmin(page: Page) {
  await page.goto('/login')
  await page.fill('input[name="email"]', 'admin@stockwire.app')
  await page.fill('input[name="password"]', 'admin')
  await page.click('button[type="submit"]')
  await page.waitForURL('/')
}
```

### E2E Test Coverage

| Test | Coverage |
|------|----------|
| setup-login-create-user | Auth flow, user creation |
| finance-transaction-flow | Transaction CRUD |
| inventory-settings-custom-fields | Custom fields |
| labels-template-flow | Label templates |
| scan-device-lifecycle | Device scanning |

---

## CI/CD Testing

### GitHub Actions

**ci.yml** (Frontend):
1. Install dependencies
2. Run unit tests
3. Build frontend
4. Run E2E tests

**backend-ci.yml** (Backend):
1. Install dependencies
2. Run pytest
3. Validate Alembic migrations

### Running CI Locally

```bash
# Frontend CI
docker compose -f infra/compose/docker-compose.dev.yml run --rm frontend npm run test:smoke
docker compose -f infra/compose/docker-compose.dev.yml run --rm frontend npm run build

# Backend CI
docker compose -f infra/compose/docker-compose.yml run --rm backend pytest
```

---

## Best Practices

### General

- Write tests for new features
- Update tests when modifying behavior
- Keep tests fast and focused
- Use descriptive test names

### Backend

- Use in-memory SQLite for tests
- Isolate tests with fixtures
- Test both success and error cases
- Mock external services

### Frontend

- Test component behavior, not implementation
- Use factories for test data
- Mock API calls
- Test accessibility

### E2E

- Keep tests independent
- Use page objects for common flows
- Test critical user journeys
- Run in CI on every PR

---

## Test Data

### Backend

Tests use SQLite in-memory database with auto-created schema.

### Frontend

Tests use fake-indexeddb for offline store tests.

### E2E

E2E tests run against a real database with seeded data.

---

## Debugging Tests

### Backend

```bash
# Run with pdb
pytest -s --pdb tests/test_api_crud.py::test_create_product

# Verbose output
pytest -v --tb=short
```

### Frontend

```bash
# Vitest with UI
npx vitest --ui

# Playwright debug
npx playwright test --debug
```

### E2E

```bash
# Show trace
npx playwright show-trace test-results/trace.zip

# HTML report
npx playwright show-report
```

---

## Coverage Reports

### Backend

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Frontend

```bash
npx vitest --coverage
open coverage/index.html
```

---

## Common Issues

### Backend

- **Database locked** - Use separate test database
- **Fixture conflicts** - Check fixture scope
- **Slow tests** - Use in-memory SQLite

### Frontend

- **IndexDB errors** - Ensure setup file loaded
- **Component not found** - Check import path
- **Async issues** - Use `await` properly

### E2E

- **Timeout** - Increase timeout or optimize test
- **Flaky tests** - Add proper waits
- **Element not found** - Use better selectors
