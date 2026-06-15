from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.domain.audit.router import router as audit_router
from app.domain.auth.router import router as auth_router
from app.domain.custom_fields.router import router as custom_fields_router
from app.domain.customers.router import router as customers_router
from app.domain.finance.router import router as finance_router
from app.domain.inventory.router import router as inventory_router
from app.domain.jobs.router import router as jobs_router
from app.domain.projects.router import router as projects_router
from app.domain.realtime.router import router as realtime_router
from app.domain.settings.router import router as settings_router
from app.domain.storage.router import router as storage_router
from app.domain.venues.router import router as venues_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(inventory_router)
api_router.include_router(custom_fields_router)
api_router.include_router(customers_router)
api_router.include_router(jobs_router)
api_router.include_router(projects_router)
api_router.include_router(realtime_router)
api_router.include_router(venues_router)
api_router.include_router(finance_router)
api_router.include_router(settings_router)
api_router.include_router(storage_router)
