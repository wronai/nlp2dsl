"""
Fixtures for worker unit tests.

Makes the worker package importable from the repo root and skips the suite
cleanly when runtime dependencies are missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

try:
    from worker import ACTION_HANDLERS, app
    from httpx import ASGITransport, AsyncClient
except ImportError as exc:
    pytest.skip(f"Skipping worker tests because a runtime dependency is missing: {exc}", allow_module_level=True)


@pytest.fixture
async def client():
    """Async HTTP client bound to the worker FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
