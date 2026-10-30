from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    # Provider-only tools can load settings without a database connection.
    database_url: str | None = Field(default=None, min_length=1)
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    app_env: str = "development"
    hf_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("database_url")
    @classmethod
    def reject_blank_database_url(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("DATABASE_URL must not be blank when supplied")
        return value

    @field_validator("frontend_url")
    @classmethod
    def reject_wildcard_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("FRONTEND_URL must contain explicit origins")
        return value

    @property
    def frontend_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.frontend_url.split(",")
            if origin.strip()
        ]


class DatabaseSettings(Settings):
    """Required configuration for the database-backed API and migrations."""

    database_url: str = Field(
        min_length=1,
        description="DATABASE_URL is required for the API and migrations",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()
