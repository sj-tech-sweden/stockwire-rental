# Metrics & Monitoring Guide

## Overview

The stack exposes Prometheus metrics at three levels:

| Source | Endpoint | Scraped by |
|--------|----------|------------|
| FastAPI backend | `GET /metrics` | Prometheus |
| Nginx (frontend) | `GET /metrics` → proxies to backend | Prometheus |
| Browser (Vue) | `POST /api/v1/metrics/frontend/*` | pushed to backend |

## Quick Start

```bash
docker compose -f infra/compose/docker-compose.yml up -d
```

Services that start:

| Service | Port | Default credentials |
|---------|------|---------------------|
| Prometheus | `9090` | `admin` / `prometheus` |
| Grafana | `3000` | anonymous access enabled (admin in docker logs on first run) |
| App (backend) | `8000` | — |
| App (frontend) | `9000` | — |

> **Note:** Prometheus web UI is protected by basic auth. Grafana dashboards are
> visible without login (anonymous access) — to make changes you must sign in as
> `admin` (password is printed in `docker logs grafana` on first startup).

## Prometheus Web UI Authentication

The Prometheus UI (`http://localhost:9090`) is protected by basic auth.

### Default credentials

- **Username:** `admin`
- **Password:** `prometheus`

### Changing the password

Generate a new bcrypt hash:

```bash
# Option A — using htpasswd (from apache2-utils)
htpasswd -nB admin | cut -d: -f2

# Option B — using the Prometheus bcrypt-hash tool
docker run --rm quay.io/prometheus/bcrypt-hash -c "$(openssl passwd -5 'your-new-password')"
```

Replace the hash in `infra/compose/prometheus-web.yml`:

```yaml
basic_auth_users:
  admin: $2y$10$...your-new-hash...
```

Then restart Prometheus:

```bash
docker compose -f infra/compose/docker-compose.yml restart prometheus
```

### Disabling web UI auth

Delete or comment out the `--web.config.file` flag in `docker-compose.yml` under
the `prometheus` service command, and remove the `prometheus-web.yml` volume mount.

## Metrics Endpoint Authentication

The backend `/metrics` endpoint is also protected by HTTP Basic Auth.
This prevents unauthorized access to your application metrics from anyone
who can reach port 8000 (backend) or port 9000 (nginx proxy).

### Default credentials

- **Username:** `prometheus`
- **Password:** `metrics`

### How it works

The check is in `backend/app/services/metrics.py`. When both
`PROMETHEUS_METRICS_USER` and `PROMETHEUS_METRICS_PASSWORD` are set (non-empty),
the `/metrics` endpoint requires a valid `Authorization: Basic ...` header.
If either is empty, the endpoint is open (no auth).

### Changing the credentials

Set the environment variables in your `.env` file:

```dotenv
PROMETHEUS_METRICS_USER=myuser
PROMETHEUS_METRICS_PASSWORD=mypassword
```

Then update the matching credentials in `infra/compose/prometheus.yml`:

```yaml
basic_auth:
  username: myuser
  password: mypassword
```

Finally restart both services:

```bash
docker compose -f infra/compose/docker-compose.yml restart backend prometheus
```

### Disabling metrics endpoint auth

Leave both env vars empty:

```dotenv
PROMETHEUS_METRICS_USER=
PROMETHEUS_METRICS_PASSWORD=
```

And remove the `basic_auth` block from `infra/compose/prometheus.yml`.

## Grafana

Grafana is provisioned automatically with:

1. **Prometheus datasource** — pointed at `http://prometheus:9090`
2. **Stockwire Metrics dashboard** — imported on startup

### Dashboard layout

| Panel | Metric | Description |
|-------|--------|-------------|
| HTTP Request Rate | `http_requests_total` | Requests per second grouped by status class |
| Request Duration | `http_request_duration_seconds` | p50 / p95 / p99 latency |
| Active Requests | `http_requests_in_progress` | Currently in-flight requests |
| Entity Counts | `app_entities` | Current count of jobs, customers, venues, projects |
| Create Rate | `app_created_total` | Creates per second by entity type |
| Delete Rate | `app_deleted_total` | Deletes per second by entity type |
| Frontend Page Views | `app_frontend_page_views_total` | Page views per second from the browser |
| Frontend API Duration | `app_frontend_api_duration_seconds` | Average API round-trip from the browser |
| Frontend Errors | `app_frontend_errors_total` | Client-side errors per second |

### Manual import

If you need to re-import the dashboard manually:

1. Open Grafana (`http://localhost:3000`)
2. Dashboards → New → Import
3. Paste the contents of `infra/compose/grafana/dashboards/stockwire-metrics.json`
4. Select the Prometheus datasource

## Metrics Reference

### Auto-instrumented (prometheus-fastapi-instrumentator)

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_seconds` | Histogram | `method`, `handler`, `status_group` |
| `http_requests_total` | Counter | `method`, `handler`, `status_group` |
| `http_requests_in_progress` | Gauge | `method` |

### Custom business metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `app_created_total` | Counter | `entity` | Total entity creates (job, customer, venue, project) |
| `app_deleted_total` | Counter | `entity` | Total entity deletes |
| `app_entities` | Gauge | `entity` | Current entity count |

### Frontend metrics (pushed from browser)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `app_frontend_page_views_total` | Counter | `path` | Page views from Vue router |
| `app_frontend_api_duration_seconds` | Histogram | `method`, `endpoint` | API call round-trip from browser |
| `app_frontend_errors_total` | Counter | `type` | Client-side errors (api_error) |

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_ENABLED` | `true` | Set to `false` to disable metrics collection entirely |
| `PROMETHEUS_METRICS_USER` | `prometheus` | Basic auth user for the `/metrics` endpoint (empty = no auth) |
| `PROMETHEUS_METRICS_PASSWORD` | `metrics` | Basic auth password for the `/metrics` endpoint (empty = no auth) |

### Disabling metrics

Set `PROMETHEUS_ENABLED=false` in the backend environment to skip instrumentator
setup and the `/metrics` endpoint entirely.

## Verifying it works

1. **Backend metrics** — `curl -u prometheus:metrics http://localhost:8000/metrics`
2. **Via nginx** — `curl -u prometheus:metrics http://localhost:9000/metrics`
3. **Prometheus targets** — `http://localhost:9090/targets` (login with `admin` / `prometheus`)
3. **Grafana dashboard** — `http://localhost:3000/d/stockwire-metrics`
4. **Frontend metrics** — navigate the app, then check `app_frontend_page_views_total` in Prometheus
