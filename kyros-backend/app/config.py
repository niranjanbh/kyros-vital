from typing import Any

from pydantic import field_validator
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

    # CORS — comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:8081,exp://localhost:8081"

    # Admin panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash — set via `python -m app.admin.cli set-password`
    SENTRY_DASHBOARD_URL: str = ""
    UPTIME_DASHBOARD_URL: str = ""
    ADMIN_SESSION_TIMEOUT_MINUTES: int = 60  # informational only in Phase 1

    @field_validator("ENV")
    @classmethod
    def _valid_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENV must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("SIGNING_SECRET")
    @classmethod
    def _signing_secret_not_default(cls, v: str, info: Any) -> str:
        env = (info.data or {}).get("ENV", "development")
        if env == "production" and v == "change-me-in-production":
            raise ValueError("SIGNING_SECRET must be changed before deploying to production")
        return v

    @field_validator("ADMIN_PASSWORD_HASH")
    @classmethod
    def _admin_hash_required_in_prod(cls, v: str, info: Any) -> str:
        env = (info.data or {}).get("ENV", "development")
        if env == "production" and not v:
            raise ValueError("ADMIN_PASSWORD_HASH must be set in production")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
