import base64

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

from app.config import settings

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[
        "/metrics",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/metrics/frontend/page-view",
        "/api/v1/metrics/frontend/api-timing",
        "/api/v1/metrics/frontend/error",
    ],
    env_var_name="PROMETHEUS_ENABLED",
)

# ── Business counters (incremented on CRUD) ──────────────────────────
created_total = Counter(
    "app_created_total",
    "Total creates by entity type",
    ["entity"],
)
deleted_total = Counter(
    "app_deleted_total",
    "Total deletes by entity type",
    ["entity"],
)

# ── Current-state gauges ─────────────────────────────────────────────
entities_count = Gauge(
    "app_entities",
    "Current count of entities by type",
    ["entity"],
)

# ── Frontend metrics (pushed from browser) ───────────────────────────
frontend_page_views = Counter(
    "app_frontend_page_views_total",
    "Page views tracked from the frontend",
    ["path"],
)
frontend_api_duration = Histogram(
    "app_frontend_api_duration_seconds",
    "API call duration from the frontend",
    ["method", "endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)
frontend_errors = Counter(
    "app_frontend_errors_total",
    "Errors tracked from the frontend",
    ["type"],
)


def _check_metrics_auth(request: Request) -> bool:
    user = settings.prometheus_metrics_user
    password = settings.prometheus_metrics_password
    if not user or not password:
        return True
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header.removeprefix("Basic ")).decode()
        provided_user, _, provided_pass = decoded.partition(":")
        return provided_user == user and provided_pass == password
    except Exception:
        return False


def setup_metrics(app: FastAPI) -> None:
    if not settings.prometheus_enabled:
        return

    instrumentator.instrument(app)

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> Response:
        if not _check_metrics_auth(request):
            return Response(status_code=401, content="Unauthorized", media_type="text/plain")
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
