from fastapi import APIRouter, Body

from app.services.metrics import (
    frontend_page_views,
    frontend_api_duration,
    frontend_errors,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/frontend/page-view")
def record_frontend_page_view(path: str = Body("")) -> dict[str, str]:
    frontend_page_views.labels(path=path or "/").inc()
    return {"ok": "true"}


@router.post("/frontend/api-timing")
def record_frontend_api_timing(
    method: str = Body("UNKNOWN"),
    endpoint: str = Body(""),
    duration_seconds: float = Body(0.0),
) -> dict[str, str]:
    frontend_api_duration.labels(method=method, endpoint=endpoint or "/").observe(duration_seconds)
    return {"ok": "true"}


@router.post("/frontend/error")
def record_frontend_error(type: str = Body("unknown")) -> dict[str, str]:
    frontend_errors.labels(type=type).inc()
    return {"ok": "true"}
