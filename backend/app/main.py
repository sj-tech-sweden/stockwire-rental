from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.domain.auth.security import validate_api_key_pepper, validate_password_pepper
import os
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if settings.prometheus_enabled:
    from app.services.metrics import setup_metrics
    setup_metrics(app)


@app.on_event("startup")
def run_startup_checks() -> None:
    # Fail fast if API_KEY_PEPPER or PASSWORD_PEPPER are misconfigured in non-dev/test environments
    validate_api_key_pepper()
    validate_password_pepper()
    # Optionally run alembic migrations on startup when MIGRATE_ON_STARTUP=true
    if os.getenv("MIGRATE_ON_STARTUP", "").lower() == "true":
        base_dir = Path(__file__).resolve().parents[1]
        alembic_cfg_path = base_dir / "alembic.ini"
        if alembic_cfg_path.exists():
            cfg = AlembicConfig(str(alembic_cfg_path))
            # set script location relative to package
            cfg.set_main_option("script_location", str(base_dir / "alembic"))
            alembic_command.upgrade(cfg, "head")
        else:
            print("alembic.ini not found; skipping automatic migrations")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "env": settings.app_env}
