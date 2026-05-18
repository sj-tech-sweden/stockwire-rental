from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EventCore Unified API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "eventcore"
    postgres_user: str = "eventcore"
    postgres_password: str = "eventcore"

    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


settings = Settings()
