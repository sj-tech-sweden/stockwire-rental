from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.domain.auth.router import router as auth_router
from app.domain.finance.router import router as finance_router
from app.domain.inventory.router import router as inventory_router
from app.domain.jobs.router import router as jobs_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(inventory_router)
api_router.include_router(jobs_router)
api_router.include_router(finance_router)
