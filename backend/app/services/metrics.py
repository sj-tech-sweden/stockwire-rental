import base64
from typing import List, Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import routing as prom_routing
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Mount, Route
from starlette.types import Scope
from fastapi import FastAPI

from app.config import settings


def _get_route_name_fixed(
    scope: Scope, routes: List[Route], route_name: Optional[str] = None
) -> Optional[str]:
    """Gets route name for given scope taking mounts into account.
    
    Fixed version that handles _IncludedRouter objects (FastAPI's router inclusion)
    which don't have a 'path' attribute but have 'original_router' with routes.
    """
    for route in routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            if hasattr(route, "path"):
                route_name = route.path
            elif hasattr(route, "original_router") and hasattr(route.original_router, "routes"):
                # Handle _IncludedRouter - recurse into its routes
                child_route_name = _get_route_name_fixed(
                    {**scope, **child_scope}, route.original_router.routes, route_name
                )
                if child_route_name is not None:
                    route_name = child_route_name
                else:
                    route_name = None
            child_scope = {**scope, **child_scope}
            if isinstance(route, Mount) and route.routes:
                child_route_name = _get_route_name_fixed(child_scope, route.routes, route_name)
                if child_route_name is None:
                    route_name = None
                else:
                    route_name += child_route_name
            return route_name
        elif match == Match.PARTIAL and route_name is None:
            if hasattr(route, "path"):
                route_name = route.path
    return None


def get_route_name_fixed(request) -> Optional[str]:
    """Gets route name for given request taking mounts into account."""
    app = request.app
    scope = request.scope
    routes = app.routes
    route_name = _get_route_name_fixed(scope, routes)

    if not route_name and app.router.redirect_slashes and scope["path"] != "/":
        redirect_scope = dict(scope)
        if scope["path"].endswith("/"):
            redirect_scope["path"] = scope["path"][:-1]
            trim = True
        else:
            redirect_scope["path"] = scope["path"] + "/"
            trim = False

        route_name = _get_route_name_fixed(redirect_scope, routes)
        if route_name is not None:
            route_name = route_name + "/" if trim else route_name[:-1]
    return route_name


# Monkey-patch the routing module to handle _IncludedRouter
prom_routing._get_route_name = _get_route_name_fixed
prom_routing.get_route_name = get_route_name_fixed

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
