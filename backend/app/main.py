from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings, validate_jwt_secret
from app.domain.integrations.twenty_webhook import router as twenty_webhook_router  # noqa: F401
from app.db.session import engine
from app.domain.auth.security import validate_api_key_pepper, validate_password_pepper
from app.domain.integrations.auto_sync import start_twenty_auto_sync, stop_twenty_auto_sync
from app.domain.warehouse_leds.mqtt_client import start_mqtt_client, stop_mqtt_client
import os
import logging
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, enabled=settings.app_env != "test")

app = FastAPI(title=settings.app_name)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS (restricted methods and headers)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Refresh-Token"],
)

# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # HSTS only when served over HTTPS (e.g., behind a reverse proxy)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


app.include_router(twenty_webhook_router)
app.include_router(api_router)

if os.environ.get("PROMETHEUS_ENABLED", "true").lower() == "true" and settings.prometheus_enabled:
    from app.services.metrics import setup_metrics
    setup_metrics(app)


def _ensure_notification_columns() -> None:
    """Ensure notification system columns exist (fallback if migration hasn't run)."""
    try:
        with engine.connect() as conn:
            # Check for recipient_type column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='notification_templates' AND column_name='recipient_type'"
            ))
            if not result.fetchone():
                logger.info("Adding missing notification system columns...")
                conn.execute(text("ALTER TABLE notification_templates ADD COLUMN IF NOT EXISTS locale VARCHAR(10) NOT NULL DEFAULT 'en'"))
                conn.execute(text("ALTER TABLE notification_templates ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT true"))
                conn.execute(text("ALTER TABLE notification_templates ADD COLUMN IF NOT EXISTS recipient_type VARCHAR(20) NOT NULL DEFAULT 'both'"))
                conn.execute(text("ALTER TABLE notification_templates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE notification_logs ADD COLUMN IF NOT EXISTS locale VARCHAR(10)"))
                conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(10) DEFAULT 'en'"))

                # Drop old single-column unique index/constraint
                conn.execute(text("DROP INDEX IF EXISTS ix_notification_templates_template_key"))
                conn.execute(text("ALTER TABLE notification_templates DROP CONSTRAINT IF EXISTS ix_notification_templates_template_key"))
                conn.execute(text("ALTER TABLE notification_templates ADD CONSTRAINT uq_template_key_locale UNIQUE (template_key, locale)"))
                # Create notification_preferences table if not exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS notification_preferences (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(80) NOT NULL UNIQUE,
                        label VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        email_enabled BOOLEAN NOT NULL DEFAULT true,
                        web_push_enabled BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """))

                # Create user_notification_preferences table if not exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_notification_preferences (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        event_type VARCHAR(80) NOT NULL,
                        email_enabled BOOLEAN NOT NULL DEFAULT true,
                        web_push_enabled BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, event_type)
                    )
                """))

                conn.commit()
                logger.info("Notification system columns added successfully")
    except Exception as e:
        logger.warning(f"Failed to ensure notification columns: {e}")


@app.on_event("startup")
def run_startup_checks() -> None:
    # Fail fast if API_KEY_PEPPER or PASSWORD_PEPPER are misconfigured in non-dev/test environments
    validate_api_key_pepper()
    validate_password_pepper()
    # Fail fast if JWT_SECRET_KEY is the default placeholder in production
    validate_jwt_secret()
    # Ensure notification system columns exist (dev/test fallback only; production
    # should rely on Alembic migrations to avoid startup DDL on every boot).
    if settings.app_env in ("development", "test"):
        _ensure_notification_columns()
    # Start MQTT client for warehouse LED integration
    start_mqtt_client()
    # Start Twenty CRM periodic auto-sync scheduler (skip in test environment)
    if settings.app_env != "test":
        start_twenty_auto_sync()
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


@app.on_event("shutdown")
def run_shutdown() -> None:
    stop_mqtt_client()
    stop_twenty_auto_sync()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "env": settings.app_env}
