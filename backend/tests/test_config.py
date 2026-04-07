"""
Tests for BackendSettings — pydantic-settings config validation.

Tests: defaults, env var override, URL coercion, LOG_LEVEL handling.
"""

from __future__ import annotations

import pytest


class TestBackendSettingsDefaults:
    """BackendSettings reads sane defaults when env vars are absent."""

    def test_worker_url_default(self, monkeypatch):
        monkeypatch.delenv("WORKER_URL", raising=False)
        monkeypatch.delenv("NLP_SERVICE_URL", raising=False)
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.worker_url == "http://worker:8000"

    def test_nlp_service_url_default(self, monkeypatch):
        monkeypatch.delenv("NLP_SERVICE_URL", raising=False)
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.nlp_service_url == "http://nlp-service:8002"

    def test_postgres_url_default_none(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.postgres_url is None

    def test_log_level_default(self, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.log_level == "INFO"


class TestBackendSettingsEnvOverride:
    """BackendSettings picks up values from env vars."""

    def test_worker_url_from_env(self, monkeypatch):
        monkeypatch.setenv("WORKER_URL", "http://custom-worker:9000")
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.worker_url == "http://custom-worker:9000"

    def test_postgres_url_from_env(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@db:5432/mydb")
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.postgres_url == "postgresql://user:pass@db:5432/mydb"

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        from app.config import BackendSettings
        s = BackendSettings()
        assert s.log_level == "DEBUG"

    def test_extra_env_vars_ignored(self, monkeypatch):
        monkeypatch.setenv("TOTALLY_UNKNOWN_VAR", "value")
        from app.config import BackendSettings
        s = BackendSettings()
        assert not hasattr(s, "totally_unknown_var")


class TestBackendSettingsIntegration:
    """BackendSettings singleton is importable and functional."""

    def test_settings_singleton_importable(self):
        from app.config import settings
        assert settings is not None
        assert hasattr(settings, "worker_url")
        assert hasattr(settings, "nlp_service_url")
        assert hasattr(settings, "postgres_url")
        assert hasattr(settings, "log_level")

    def test_engine_uses_settings(self):
        """engine.py reads WORKER_URL and NLP_SERVICE_URL from settings."""
        from app.engine import WORKER_URL, NLP_SERVICE_URL
        assert "://" in WORKER_URL
        assert "://" in NLP_SERVICE_URL
