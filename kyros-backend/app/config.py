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

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
