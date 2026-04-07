"""
Settings Manager — runtime konfiguracja systemu.

Ustawienia można zmieniać:
  - przez API (/settings/...)
  - przez konwersację ("zmień model na gpt-4o")
  - przez edycję pliku settings.json

Persystencja: JSON file (MVP) → Redis/Postgres w produkcji.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings as _svc_config

log = logging.getLogger("settings")

SETTINGS_FILE = _svc_config.settings_file


# ── Settings Schema ──────────────────────────────────────────


class LLMSettings(BaseModel):
    provider: str = "openrouter"
    model: str = "openrouter/openai/gpt-5-mini"
    temperature: float = 0.0
    max_tokens: int = 1024
    api_base: str | None = None
    fallback_threshold: float = 0.5


class NLPSettings(BaseModel):
    default_mode: str = "auto"          # auto | rules | llm
    default_language: str = "pl"        # pl | en
    confidence_threshold: float = 0.5


class WorkerSettings(BaseModel):
    timeout_seconds: int = int("120")
    retry_count: int = 0
    fail_fast: bool = True


class FileAccessSettings(BaseModel):
    allowed_paths: list[str] = [
        "/app",
        "/home/claude/mvp-automation",
    ]
    read_only_paths: list[str] = [
        "/app/app",          # NLP service code
    ]
    max_file_size_kb: int = 512
    allowed_extensions: list[str] = [
        ".py", ".yml", ".yaml", ".json", ".txt", ".md",
        ".env", ".toml", ".cfg", ".ini", ".sh",
    ]


class SystemSettings(BaseModel):
    """Pełny model ustawień systemu."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    nlp: NLPSettings = Field(default_factory=NLPSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    file_access: FileAccessSettings = Field(default_factory=FileAccessSettings)
    updated_at: str | None = None
    version: str = "0.2.0"


# ── Settings Manager (Singleton) ─────────────────────────────


class SettingsManager:
    """Runtime settings z persystencją do JSON."""

    _instance: SettingsManager | None = None
    _settings: SystemSettings

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SystemSettings()
            cls._instance._load()
        return cls._instance

    # ── Read ──

    @property
    def settings(self) -> SystemSettings:
        return self._settings

    def get(self, path: str) -> Any:  # noqa: ANN401
        """Get setting by dot-path: 'llm.model', 'worker.timeout_seconds'."""
        parts = path.split(".")
        obj = self._settings
        for part in parts:
            if isinstance(obj, BaseModel):
                obj = getattr(obj, part, None)
            elif isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
            if obj is None:
                return None
        return obj

    def get_section(self, section: str) -> dict:
        """Get full section as dict: 'llm', 'nlp', 'worker'."""
        obj = getattr(self._settings, section, None)
        if obj and isinstance(obj, BaseModel):
            return obj.model_dump()
        return {}

    def get_all(self) -> dict:
        """Get all settings as dict."""
        return self._settings.model_dump()

    # ── Write ──

    def set(self, path: str, value: Any) -> dict:  # noqa: ANN401
        """Set setting by dot-path. Returns {"old": ..., "new": ..., "path": ...}."""
        parts = path.split(".")
        obj = self._settings

        # Navigate to parent
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                raise ValueError(f"Setting path '{path}' not found")

        field = parts[-1]
        old_value = getattr(obj, field, None)

        # Type coercion
        if old_value is not None:
            value = _coerce_type(value, type(old_value))

        setattr(obj, field, value)
        self._settings.updated_at = datetime.now(UTC).isoformat()
        self._save()

        log.info("Setting changed: %s = %s → %s", path, old_value, value)
        return {"path": path, "old": old_value, "new": value}

    def update_section(self, section: str, data: dict) -> dict:
        """Update entire section from dict."""
        obj = getattr(self._settings, section, None)
        if obj is None:
            raise ValueError(f"Section '{section}' not found")

        changes = []
        for key, value in data.items():
            if hasattr(obj, key):
                old = getattr(obj, key)
                if old != value:
                    setattr(obj, key, value)
                    changes.append({"field": key, "old": old, "new": value})

        if changes:
            self._settings.updated_at = datetime.now(UTC).isoformat()
            self._save()

        return {"section": section, "changes": changes}

    def reset(self, section: str | None = None) -> dict:
        """Reset settings to defaults."""
        if section:
            default = SystemSettings()
            setattr(self._settings, section, getattr(default, section))
        else:
            self._settings = SystemSettings()

        self._settings.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return {"reset": section or "all"}

    # ── Persistence ──

    def _load(self) -> None:
        path = Path(SETTINGS_FILE)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._settings = SystemSettings(**data)
                log.info("Settings loaded from %s", SETTINGS_FILE)
            except Exception as e:
                log.warning("Failed to load settings: %s, using defaults", e)

    def _save(self) -> None:
        path = Path(SETTINGS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(self._settings.model_dump_json(indent=2))
        except Exception as e:
            log.warning("Failed to save settings: %s", e)

    # ── Describe (for NLP/UI) ──

    @staticmethod
    def describe() -> dict:
        """Return settings schema for UI/NLP — what can be changed."""
        return {
            "llm": {
                "model":      {"type": "string", "label": "Model LLM", "examples": ["openrouter/openai/gpt-5-mini", "gpt-4o-mini", "claude-sonnet-4-20250514"]},
                "provider":   {"type": "select", "label": "Provider", "options": ["openrouter", "openai", "anthropic", "ollama", "groq", "together", "mistral"]},
                "temperature": {"type": "number", "label": "Temperatura", "min": 0, "max": 2},
                "max_tokens":  {"type": "number", "label": "Max tokenów", "min": 256, "max": 16384},
                "fallback_threshold": {"type": "number", "label": "Próg fallback do LLM", "min": 0, "max": 1},
            },
            "nlp": {
                "default_mode":    {"type": "select", "label": "Tryb NLP", "options": ["auto", "rules", "llm"]},
                "default_language": {"type": "select", "label": "Język", "options": ["pl", "en"]},
                "confidence_threshold": {"type": "number", "label": "Próg confidence", "min": 0, "max": 1},
            },
            "worker": {
                "timeout_seconds": {"type": "number", "label": "Timeout (s)", "min": int("10"), "max": int("600")},
                "retry_count":     {"type": "number", "label": "Ponowne próby", "min": 0, "max": 5},
                "fail_fast":       {"type": "boolean", "label": "Fail-fast"},
            },
            "file_access": {
                "max_file_size_kb":    {"type": "number", "label": "Max rozmiar pliku (KB)"},
                "allowed_extensions":  {"type": "list", "label": "Dozwolone rozszerzenia"},
            },
        }


# ── Helpers ───────────────────────────────────────────────────


def _coerce_type(value: Any, target_type: type) -> Any:  # noqa: ANN401
    """Coerce value to target type."""
    if target_type is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "tak")
        return bool(value)
    if target_type is int:
        return int(float(value))
    if target_type is float:
        return float(value)
    return value


# ── Module-level singleton ────────────────────────────────────

settings_manager = SettingsManager()
