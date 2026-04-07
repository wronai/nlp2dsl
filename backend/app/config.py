"""
Backend configuration — single source of truth for all environment variables.

All settings read from environment variables (or .env file) at startup.
Missing required variables raise ValidationError immediately — fail-fast.

Usage:
    from .config import settings
    url = settings.worker_url
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    worker_url: str = Field(
        default="http://worker:8000",
        description="URL of the task worker service",
    )
    nlp_service_url: str = Field(
        default="http://nlp-service:8002",
        description="URL of the NLP service",
    )
    postgres_url: str | None = Field(
        default=None,
        description="PostgreSQL DSN — if set, enables Postgres workflow repo",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )


settings = BackendSettings()
