import json
import os
import secrets
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Stockwire Rental API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "stockwire_rental"
    postgres_user: str = "stockwire_rental"
    postgres_password: str = "stockwire_rental"

    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:9000,http://localhost:3000"

    jwt_secret_key: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    sso_enabled: bool = False
    sso_auto_create_users: bool = True
    sso_sync_roles_on_login: bool = True
    sso_default_role: str = "viewer"
    sso_group_role_map: str = "{}"
    oidc_providers: str = "{}"
    saml_providers: str = "{}"

    storage_backend: str = "local"
    storage_max_upload_mb: int = 25
    storage_local_path: str = "./data/uploads"

    storage_s3_bucket: str | None = None
    storage_s3_region: str | None = None
    storage_s3_endpoint_url: str | None = None
    storage_s3_access_key_id: str | None = None
    storage_s3_secret_access_key: str | None = None
    storage_s3_prefix: str = "uploads"
    storage_s3_presign_expiry_seconds: int = 900

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@stockwire.app"
    smtp_from_name: str = "Stockwire Rental"
    smtp_use_tls: bool = True

    resend_api_key: str = ""
    web_push_vapid_public_key: str = ""
    web_push_vapid_private_key: str = ""
    web_push_vapid_subject: str = "mailto:noreply@stockwire.app"

    password_reset_expire_minutes: int = 15
    password_reset_base_url: str = "http://localhost:9000"

    prometheus_enabled: bool = True
    prometheus_pushgateway: str = ""
    prometheus_metrics_user: str = ""
    prometheus_metrics_password: str = ""

    productionplanner_api_key: str = ""
    productionplanner_base_url: str = "https://api.productionplanner.io/v1"

    twenty_api_key: str = ""
    twenty_base_url: str = "https://api.twenty.com"
    twenty_webhook_secret: str = ""

    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "stockwire"
    mqtt_warehouse_id: str = "default"
    mqtt_tls: bool = False
    mqtt_enabled: bool = False

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5-coder"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @staticmethod
    def _parse_json_object(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @property
    def sso_group_role_map_obj(self) -> dict[str, str]:
        parsed = self._parse_json_object(self.sso_group_role_map)
        out: dict[str, str] = {}
        for key, value in parsed.items():
            group = str(key).strip()
            role = str(value).strip().lower()
            if group and role:
                out[group] = role
        return out

    @property
    def oidc_providers_obj(self) -> dict[str, dict[str, Any]]:
        parsed = self._parse_json_object(self.oidc_providers)
        out: dict[str, dict[str, Any]] = {}
        for key, value in parsed.items():
            if isinstance(value, dict):
                out[str(key)] = value
        return out

    @property
    def saml_providers_obj(self) -> dict[str, dict[str, Any]]:
        parsed = self._parse_json_object(self.saml_providers)
        out: dict[str, dict[str, Any]] = {}
        for key, value in parsed.items():
            if isinstance(value, dict):
                out[str(key)] = value
        return out


settings = Settings()

# ---------------------------------------------------------------------------
# JWT Secret Validation & Migration Helper
# ---------------------------------------------------------------------------

_JWT_SECRET_PLACEHOLDER = "change-me-in-production-use-a-long-random-string"


def validate_jwt_secret() -> None:
    """Fail fast at startup if JWT_SECRET_KEY is the default placeholder in non-dev environments."""
    raw = os.getenv("JWT_SECRET_KEY", "")
    # Allow sourcing the secret from a file (used by `--generate-jwt-secret`)
    secret_file = (os.getenv("JWT_SECRET_KEY_FILE") or "").strip()
    if not raw and secret_file and os.path.exists(secret_file):
        try:
            with open(secret_file, "r") as f:
                raw = f.read().strip()
            if raw:
                settings.jwt_secret_key = raw
        except OSError:
            raw = ""

    app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    if app_env in {"development", "test"}:
        return
    if not raw or raw == _JWT_SECRET_PLACEHOLDER:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a strong random value in production. "
            "Run: python -m app.config --generate-jwt-secret"
        )


def generate_jwt_secret() -> str:
    """Generate a cryptographically secure JWT secret key."""
    return secrets.token_urlsafe(64)


def write_jwt_secret_to_file(new_secret: str) -> str:
    """Return a pre-provisioned JWT secret file path without writing secret material.

    The JWT secret must be provisioned by external secret management (for example,
    a mounted container/KMS secret). This function validates the configured path
    and enforces restrictive permissions when possible.

    Returns the path to the secret file.
    """
    _ = new_secret
    secret_file_path = os.getenv("JWT_SECRET_FILE", ".jwt_secret")
    if not os.path.exists(secret_file_path):
        raise RuntimeError(
            "JWT_SECRET_FILE does not exist. Provision the JWT secret file via "
            "secure external secret management before running rotation."
        )
    os.chmod(secret_file_path, 0o600)
    return secret_file_path


def rotate_jwt_secret_in_env(secret_file_path: str) -> str:
    """Update or create JWT_SECRET_KEY_FILE in the .env file.

    Returns the path to the updated .env file.
    """
    env_path = os.getenv("ENV_FILE", ".env")
    env_lines: list[str] = []
    found = False

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("JWT_SECRET_KEY_FILE="):
                    env_lines.append(f"JWT_SECRET_KEY_FILE={secret_file_path}\n")
                    found = True
                elif line.strip().startswith("JWT_SECRET_KEY="):
                    env_lines.append(f"JWT_SECRET_KEY_FILE={secret_file_path}\n")
                    found = True
                else:
                    env_lines.append(line)

    if not found:
        env_lines.append(f"JWT_SECRET_KEY_FILE={secret_file_path}\n")

    with open(env_path, "w") as f:
        f.writelines(env_lines)

    return env_path

if __name__ == "__main__":
    import sys
    if "--generate-jwt-secret" in sys.argv:
        secret = generate_jwt_secret()
        print("JWT secret generated and written to file.")
        secret_file = write_jwt_secret_to_file(secret)
        path = rotate_jwt_secret_in_env(secret_file)
        print("Environment file updated with JWT_SECRET_KEY_FILE reference.")
        print("Restart the application to apply the new secret.")
    else:
        print("Usage: python -m app.config --generate-jwt-secret")
