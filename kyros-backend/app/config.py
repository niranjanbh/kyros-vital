from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://kyros:kyros@localhost:5432/kyros"
    REDIS_URL: str = "redis://localhost:6379/0"
    STORAGE_DIR: str = "./storage"
    STORAGE_BACKEND: str = "local"
    SIGNING_SECRET: str = "change-me-in-production"
    LOG_LEVEL: str = "INFO"
    ENV: str = "development"
    TESTING: bool = False

    # Admin panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash — set via `python -m app.admin.cli set-password`
    SENTRY_DASHBOARD_URL: str = ""
    UPTIME_DASHBOARD_URL: str = ""
    ADMIN_SESSION_TIMEOUT_MINUTES: int = 60  # informational only in Phase 1

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
