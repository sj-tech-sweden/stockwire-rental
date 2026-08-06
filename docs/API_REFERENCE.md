# API Overview

> Last reviewed: 2026-08-06

## Auto-Generated Documentation

Stockwire Rental uses FastAPI which auto-generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

These docs are always up-to-date and include request/response schemas, authentication requirements, and try-it-out functionality.

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Authentication

All endpoints (except `/health/*` and `/auth/login`, `/auth/setup`) require a valid JWT token:

```
Authorization: Bearer <token>
```

**Token lifecycle:**
1. `POST /auth/login` → returns `access_token` (15 min) + `refresh_token` (7 days)
2. `POST /auth/refresh` → exchange refresh token for new tokens
3. SSO flows return tokens after IdP callback

---

## API Structure

The API is organized by domain modules:

| Prefix | Domain |
|--------|--------|
| `/auth` | Authentication, users, roles, SSO |
| `/inventory` | Products, devices, zones, categories, maintenance, defects |
| `/jobs` | Jobs and requirements |
| `/customers` | Customers/companies |
| `/venues` | Venues/locations |
| `/projects` | Projects |
| `/crew` | Crew roles, members, skills, certifications |
| `/finance` | Financial transactions |
| `/settings` | App settings, integrations |
| `/storage` | File uploads/downloads |
| `/custom-fields` | Dynamic field definitions and values |
| `/notifications` | Push subscriptions, templates, dispatch |
| `/route-planner` | Vehicles, routes, stops |
| `/warehouse-leds` | LED controllers, bin mappings |
| `/calendar` | ICS feed subscriptions |
| `/integrations/twenty` | Twenty CRM sync |
| `/realtime` | WebSocket connection |
| `/metrics` | Frontend telemetry |
| `/audit` | Activity logs |
| `/assistant` | AI chat (SSE streaming) |

---

## Common Patterns

### Pagination

Most list endpoints support `skip` and `limit`:

```
GET /api/v1/inventory/products?skip=0&limit=50
```

### Filtering

Many endpoints support query parameter filtering:

```
GET /api/v1/inventory/products?category_id=uuid&search=keyword
GET /api/v1/jobs?status=active&customer_id=uuid
```

### Error Responses

```json
{
  "detail": "Error message"
}
```

### Bootstrap Endpoints

Several domains have a `/bootstrap` endpoint that returns minimal data for dropdowns:

```
GET /api/v1/jobs/bootstrap
GET /api/v1/customers/bootstrap
GET /api/v1/venues/bootstrap
```

---

## Development Tips

- Use Swagger UI (`/docs`) to explore and test endpoints interactively
- The OpenAPI spec can be imported into Postman or other API tools
- Authentication can be tested directly in Swagger UI using the "Authorize" button
