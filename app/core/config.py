"""Application configuration loaded from environment variables and `.env`."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime settings for the API and shared application services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="SQLAlchemy database URL (e.g. postgresql+psycopg://user:pass@host:5432/db).",
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="Bind address for the FastAPI server.",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for the FastAPI server.",
    )
    log_level: LogLevel = Field(
        default="INFO",
        description="Root logging verbosity.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, validating required environment variables on first call."""
    try:
        return Settings()
    except ValidationError as exc:
        missing_fields = [
            error["loc"][0]
            for error in exc.errors()
            if error["type"] == "missing"
        ]
        if missing_fields:
            field_names = ", ".join(str(name) for name in missing_fields)
            raise RuntimeError(
                "Missing required configuration. Set these environment variables "
                f"(or add them to .env): {field_names}. See .env.example for reference."
            ) from exc
        raise RuntimeError(
            "Invalid application configuration. Check environment variables and .env."
        ) from exc


settings: Settings = get_settings()
