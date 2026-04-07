"""
Tests for worker/worker.py — task execution engine.

Uses httpx.AsyncClient with ASGI transport (no real server needed).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from worker import app, ACTION_HANDLERS


@pytest.fixture
async def client():
    """Async HTTP client bound to the worker FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health ───────────────────────────────────────────────────────


class TestWorkerHealth:
    """Worker health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """GET /health → 200 with actions list."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "worker"
        assert isinstance(data["actions"], list)
        assert "send_invoice" in data["actions"]


# ── Execute actions ──────────────────────────────────────────────


class TestExecuteActions:
    """POST /execute — action execution."""

    @pytest.mark.asyncio
    async def test_execute_send_invoice(self, client: AsyncClient):
        """Execute send_invoice → completed with invoice_id."""
        resp = await client.post(
            "/execute",
            json={
                "step_id": "s1",
                "action": "send_invoice",
                "config": {"to": "klient@firma.pl", "amount": 1500, "currency": "PLN"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "invoice_id" in data["result"]
        assert data["result"]["sent_to"] == "klient@firma.pl"

    @pytest.mark.asyncio
    async def test_execute_send_email(self, client: AsyncClient):
        """Execute send_email → completed."""
        resp = await client.post(
            "/execute",
            json={
                "step_id": "s2",
                "action": "send_email",
                "config": {"to": "user@example.com", "subject": "Test"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"]["sent_to"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_execute_generate_report(self, client: AsyncClient):
        """Execute generate_report → completed with filename."""
        resp = await client.post(
            "/execute",
            json={
                "step_id": "s3",
                "action": "generate_report",
                "config": {"type": "sales", "format": "pdf"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "filename" in data["result"]

    @pytest.mark.asyncio
    async def test_execute_notify_slack(self, client: AsyncClient):
        """Execute notify_slack → completed."""
        resp = await client.post(
            "/execute",
            json={
                "step_id": "s4",
                "action": "notify_slack",
                "config": {"channel": "#general", "message": "Test"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"]["channel"] == "#general"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, client: AsyncClient):
        """Unknown action → 400 error."""
        resp = await client.post(
            "/execute",
            json={
                "step_id": "s5",
                "action": "nonexistent_action",
                "config": {},
            },
        )
        assert resp.status_code == 400
        assert "nonexistent_action" in resp.json()["detail"]


# ── Action registry ──────────────────────────────────────────────


class TestActionRegistry:
    """ACTION_HANDLERS dict validation."""

    def test_handlers_registered(self):
        """At least 5 action handlers registered."""
        assert len(ACTION_HANDLERS) >= 5

    def test_all_handlers_callable(self):
        """All registered handlers are async callables."""
        for name, handler in ACTION_HANDLERS.items():
            assert callable(handler), f"Handler for '{name}' not callable"
