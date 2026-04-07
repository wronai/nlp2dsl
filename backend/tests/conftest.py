"""
Fixtures for backend unit tests.

Provides AsyncClient for testing FastAPI endpoints
and mocks for external service calls (worker, nlp-service).
"""

from __future__ import annotations

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    """Async HTTP client bound to the backend FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
