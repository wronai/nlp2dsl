"""
NLP-service configuration — single source of truth for all environment variables.

All settings read from environment variables (or .env file) at startup.
Missing required variables raise ValidationError immediately — fail-fast.

Usage:
    from .config import settings
    ttl = settings.conversation_ttl
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NLPServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: str | None = Field(
        default=None,
        description="Redis DSN — if set, enables Redis conversation store",
    )
    conversation_ttl: int = Field(
        default=3600,
        description="Conversation TTL in seconds (Redis sliding expiry)",
    )
    llm_fallback_threshold: float = Field(
        default=0.5,
        description="Confidence threshold below which LLM fallback is triggered",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    deepgram_api_key: str | None = Field(
        default=None,
        description="Deepgram API key for STT — optional",
    )
    deepgram_model: str = Field(
        default="nova-3-general",
        description="Deepgram STT model",
    )
    deepgram_language: str = Field(
        default="pl",
        description="Deepgram STT language code",
    )

    settings_file: str = Field(
        default="/app/data/settings.json",
        description="Path to persistent settings JSON file",
    )


settings = NLPServiceSettings()
