"""
Fixtures for backend unit tests.

Provides AsyncClient for testing FastAPI endpoints
and mocks for external service calls (worker, nlp-service).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from app.main import app
    from httpx import ASGITransport, AsyncClient
except ImportError as exc:
    pytest.skip(f"Skipping backend tests because a runtime dependency is missing: {exc}", allow_module_level=True)


@pytest.fixture
async def client():
    """Async HTTP client bound to the backend FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
