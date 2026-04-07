"""
Structured logging — JSON format + X-Request-ID trace.

Components:
  JSONFormatter        — log records as JSON lines with ts, level, service, request_id, msg
  RequestIDMiddleware  — generate/propagate X-Request-ID per HTTP request via contextvars
  setup_logging()      — apply JSONFormatter to root logger, replace basicConfig

Usage (in main.py):
  from .logging_setup import setup_logging, RequestIDMiddleware
  setup_logging(service="backend")
  app.add_middleware(RequestIDMiddleware)
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def __init__(self, service: str = "app") -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self._service,
            "request_id": _request_id.get(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generate or forward X-Request-ID for every HTTP request.

    - Reads X-Request-ID from incoming headers if present (cross-service trace).
    - Generates a new UUID otherwise.
    - Stores the ID in a ContextVar so all log calls within the request include it.
    - Adds X-Request-ID to the response headers.
    """

    def __init__(self, app: ASGIApp, header: str = "X-Request-ID") -> None:
        super().__init__(app)
        self._header = header

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(self._header) or uuid4().hex
        token = _request_id.set(request_id)
        try:
            response = await call_next(request)
            response.headers[self._header] = request_id
            return response
        finally:
            _request_id.reset(token)


def setup_logging(service: str = "app", level: str | None = None) -> None:
    """
    Replace root logger handlers with a JSONFormatter handler.

    Reads LOG_LEVEL from BackendSettings (default INFO). Call once at startup.
    """
    if level is None:
        try:
            from .config import settings as _cfg
            level = _cfg.log_level
        except Exception:
            level = "INFO"
    log_level = level.upper()
    numeric = getattr(logging, log_level, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter(service=service))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric)
