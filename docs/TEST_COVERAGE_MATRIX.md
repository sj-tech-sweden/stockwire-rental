# Test Coverage Matrix

Last reviewed: 2026-05-22

This matrix maps currently shipped Stockwire Rental functionality to automated test coverage and CI execution.

## Legend

- Backend tests: `backend/tests/*.py`
- Frontend unit/smoke: `frontend/tests/**/*.test.js`
- Frontend E2E: `frontend/tests/e2e/*.spec.ts`
- CI workflows: `.github/workflows/ci.yml`, `.github/workflows/backend-ci.yml`

## Coverage by domain

| Domain / Feature | Backend tests | Frontend tests | E2E tests | Enforced in CI |
| --- | --- | --- | --- | --- |
| Health/bootstrap/auth basic flow | `test_health.py`, `test_modules.py`, `test_api_crud.py::test_auth_crud` | `router.smoke.test.js`, `stores.smoke.test.js` (auth store) | `setup-login-create-user.spec.ts` | Yes |
| Inventory products/devices/zones/categories | `test_api_crud.py::test_inventory_crud`, `test_inventory_category_move_and_custom_fields` | `stores.smoke.test.js` (inventory store) | `inventory-settings-custom-fields.spec.ts`, `setup-login-create-user.spec.ts` (route smoke) | Yes |
| Jobs + requirements | `test_api_crud.py::test_jobs_and_finance_crud` | `stores.smoke.test.js` (jobs store) | `setup-login-create-user.spec.ts` (route smoke) | Yes |
| Finance transactions + summaries | `test_api_crud.py::test_jobs_and_finance_crud` | `stores.smoke.test.js` (finance store) | `setup-login-create-user.spec.ts` (route smoke) | Yes |
| Currency behavior (settings + finance format pipeline) | `test_api_crud.py::test_company_profile_currency_settings`, `test_jobs_and_finance_crud` | `unit/currencies.test.js` | Covered indirectly via route and inventory/settings e2e flows | Yes |
| Customers and venues | `test_api_crud.py::test_customers_and_venues_crud` | n/a dedicated unit yet | `setup-login-create-user.spec.ts` (route smoke) | Yes |
| Custom fields (definitions + values) | `test_api_crud.py::test_inventory_category_move_and_custom_fields` | n/a dedicated unit yet | `inventory-settings-custom-fields.spec.ts` | Yes |
| Settings modules (location types, category prefill, product defaults, integrations, auth-sso, label templates) | `test_api_crud.py::test_settings_modules_crud` | n/a dedicated unit yet | `inventory-settings-custom-fields.spec.ts` + route smoke | Yes |
| Storage/public company profile wiring | `test_api_crud.py::test_company_profile_currency_settings` | n/a dedicated unit yet | route smoke and settings flows | Yes |
| Router/main app pages | n/a | `router.smoke.test.js` | `setup-login-create-user.spec.ts` (route smoke all main routes) | Yes |

## CI enforcement

- `ci.yml`
  - frontend unit/smoke tests (`npm run test:smoke`)
  - frontend build (`npm run build`)
  - backend tests (`pytest -q`)
  - Playwright E2E across Chromium/Firefox/WebKit (no `|| true` bypass)
- `backend-ci.yml`
  - backend tests on Python 3.12
  - alembic upgrade/downgrade migration validation

## Remaining gap notes

- Frontend unit coverage for customers/venues/settings submodules can be expanded for finer-grained regression isolation.
- E2E currently focuses on high-value smoke and inventory/settings flow. Additional scenario-level E2E (scan/device lifecycle, labels, activity filtering, finance create/edit/settle) can be added incrementally.
