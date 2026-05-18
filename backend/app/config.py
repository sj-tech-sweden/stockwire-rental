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


settings = Settings()
