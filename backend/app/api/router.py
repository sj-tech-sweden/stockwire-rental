from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.domain.audit.router import router as audit_router
from app.domain.auth.router import router as auth_router
from app.domain.custom_fields.router import router as custom_fields_router
from app.domain.customers.router import router as customers_router
from app.domain.crew.router import router as crew_router
from app.domain.reports.router import router as reports_router
from app.domain.finance.router import router as finance_router
from app.domain.integrations.router import router as integrations_router
from app.domain.route_planner.router import router as route_planner_router
from app.domain.calendar_feeds.router import router as calendar_feeds_router
from app.assistant.router import router as assistant_router
from app.domain.warehouse_leds.router import router as warehouse_leds_router
from app.domain.inventory.router import router as inventory_router
from app.domain.jobs.router import router as jobs_router
from app.domain.notifications.router import router as notifications_router
from app.domain.projects.router import router as projects_router
from app.domain.realtime.router import router as realtime_router
from app.domain.settings.router import router as settings_router
from app.domain.storage.router import router as storage_router
from app.domain.venues.router import router as venues_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(metrics_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(inventory_router)
api_router.include_router(custom_fields_router)
api_router.include_router(customers_router)
api_router.include_router(crew_router)
api_router.include_router(reports_router)
api_router.include_router(jobs_router)
api_router.include_router(notifications_router)
api_router.include_router(projects_router)
api_router.include_router(realtime_router)
api_router.include_router(venues_router)
api_router.include_router(finance_router)
api_router.include_router(settings_router)
api_router.include_router(storage_router)
api_router.include_router(integrations_router)
api_router.include_router(route_planner_router)
api_router.include_router(warehouse_leds_router)
api_router.include_router(calendar_feeds_router)
api_router.include_router(assistant_router)
