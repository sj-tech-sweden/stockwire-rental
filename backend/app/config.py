import json
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

    password_reset_expire_minutes: int = 15
    password_reset_base_url: str = "http://localhost:9000"

    prometheus_enabled: bool = True
    prometheus_pushgateway: str = ""
    prometheus_metrics_user: str = ""
    prometheus_metrics_password: str = ""

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
