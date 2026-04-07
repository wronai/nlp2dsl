"""
Tests for structured logging — JSONFormatter, RequestIDMiddleware, setup_logging.
"""

from __future__ import annotations

import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient


class TestJSONFormatter:
    """JSONFormatter emits valid JSON with expected fields."""

    def test_format_produces_json(self) -> None:
        from app.logging_setup import JSONFormatter
        formatter = JSONFormatter(service="test-svc")
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO,
            pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        doc = json.loads(output)

        assert doc["level"] == "INFO"
        assert doc["service"] == "test-svc"
        assert doc["msg"] == "hello world"
        assert doc["logger"] == "test.logger"
        assert "ts" in doc
        assert "request_id" in doc

    def test_format_includes_exception(self) -> None:
        from app.logging_setup import JSONFormatter
        formatter = JSONFormatter(service="test-svc")
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0,
            msg="error occurred", args=(), exc_info=exc_info,
        )
        output = formatter.format(record)
        doc = json.loads(output)
        assert "exc" in doc
        assert "ValueError" in doc["exc"]

    def test_format_service_name(self) -> None:
        from app.logging_setup import JSONFormatter
        formatter = JSONFormatter(service="my-service")
        record = logging.LogRecord(
            name="x", level=logging.WARNING,
            pathname="", lineno=0,
            msg="warn", args=(), exc_info=None,
        )
        doc = json.loads(formatter.format(record))
        assert doc["service"] == "my-service"
        assert doc["level"] == "WARNING"


class TestRequestIDMiddleware:
    """RequestIDMiddleware adds X-Request-ID to responses."""

    @pytest.fixture
    def test_app(self):
        from app.logging_setup import RequestIDMiddleware
        from fastapi import FastAPI

        inner = FastAPI()
        inner.add_middleware(RequestIDMiddleware)

        @inner.get("/ping")
        async def ping():
            return {"ok": True}

        return inner

    async def test_response_has_request_id_header(self, test_app) -> None:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ping")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    async def test_client_request_id_is_forwarded(self, test_app) -> None:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ping", headers={"X-Request-ID": "trace-abc-123"})
        assert resp.headers["x-request-id"] == "trace-abc-123"

    async def test_new_id_generated_without_header(self, test_app) -> None:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.get("/ping")
            r2 = await client.get("/ping")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


class TestSetupLogging:
    """setup_logging() installs JSONFormatter on root logger."""

    def test_setup_logging_installs_json_handler(self) -> None:
        from app.logging_setup import JSONFormatter, setup_logging
        setup_logging(service="setup-test")

        root = logging.getLogger()
        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)

    def test_setup_logging_respects_log_level(self) -> None:
        from app.logging_setup import setup_logging
        setup_logging(service="level-test", level="WARNING")

        root = logging.getLogger()
        assert root.level == logging.WARNING
