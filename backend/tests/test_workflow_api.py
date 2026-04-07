"""
Tests for backend/app/workflow.py — workflow API endpoints.

Uses httpx.AsyncClient with ASGI transport (no real server needed).
Mocks external HTTP calls to worker and nlp-service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, Response

# ── Health ───────────────────────────────────────────────────────


class TestHealthEndpoint:
    """Backend health check."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """GET /health → 200 with status ok."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "backend"


# ── Workflow actions ─────────────────────────────────────────────


class TestWorkflowActions:
    """GET /workflow/actions endpoint."""

    @pytest.mark.asyncio
    async def test_workflow_actions(self, client: AsyncClient) -> None:
        """GET /workflow/actions → list of available actions."""
        resp = await client.get("/workflow/actions")
        assert resp.status_code == 200
        actions = resp.json()
        assert isinstance(actions, list)
        assert len(actions) > 0
        # Each action has name and description
        for action in actions:
            assert "name" in action
            assert "description" in action

    @pytest.mark.asyncio
    async def test_workflow_actions_contains_invoice(self, client: AsyncClient) -> None:
        """Actions list includes send_invoice."""
        resp = await client.get("/workflow/actions")
        names = [a["name"] for a in resp.json()]
        assert "send_invoice" in names


# ── Workflow run ─────────────────────────────────────────────────


def _mock_worker_response(status_code=200, json_data=None):
    """Create a mock httpx.Response for worker calls."""
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data or {"step_id": "s1", "status": "completed", "result": {"ok": True}}
    resp.text = ""
    resp.headers = {"content-type": "application/json"}
    return resp


class TestRunWorkflow:
    """POST /workflow/run endpoint."""

    @pytest.mark.asyncio
    async def test_run_workflow(self, client: AsyncClient) -> None:
        """Successful single-step workflow execution."""
        mock_resp = _mock_worker_response(
            json_data={"step_id": "step1", "status": "completed", "result": {"invoice_id": "INV-001"}}
        )

        with patch("app.engine.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/run",
                json={
                    "name": "test_workflow",
                    "steps": [
                        {"action": "send_invoice", "config": {"to": "x@y.pl", "amount": 100}}
                    ],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert len(data["steps"]) == 1

    @pytest.mark.asyncio
    async def test_run_workflow_step_failure(self, client: AsyncClient) -> None:
        """Failed step → 400 with error details."""
        mock_resp = _mock_worker_response(status_code=500)
        mock_resp.text = "Internal Server Error"

        with patch("app.engine.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/run",
                json={
                    "name": "fail_workflow",
                    "steps": [{"action": "send_invoice", "config": {}}],
                },
            )
            assert resp.status_code == 400


# ── Workflow history ─────────────────────────────────────────────


class TestWorkflowHistory:
    """GET /workflow/history endpoint."""

    @pytest.mark.asyncio
    async def test_workflow_history(self, client: AsyncClient) -> None:
        """GET /workflow/history → list (possibly empty)."""
        resp = await client.get("/workflow/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── From text ────────────────────────────────────────────────────


class TestFromText:
    """POST /workflow/from-text endpoint."""

    @pytest.mark.asyncio
    async def test_from_text_complete(self, client: AsyncClient) -> None:
        """Complete NLP response → returns DSL."""
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "status": "complete",
            "workflow": {
                "name": "auto_send_invoice",
                "trigger": "manual",
                "steps": [{"action": "send_invoice", "config": {"amount": 1500, "to": "a@b.pl"}}],
            },
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/from-text",
                json={"text": "Wyślij fakturę na 1500 PLN do a@b.pl"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "complete"
            assert "dsl" in data

    @pytest.mark.asyncio
    async def test_from_text_incomplete(self, client: AsyncClient) -> None:
        """Incomplete NLP response → returns missing fields."""
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "status": "incomplete",
            "missing_fields": ["send_invoice.to"],
            "prompt_user": "Podaj adres e-mail odbiorcy",
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/from-text",
                json={"text": "Wyślij fakturę na 500 PLN"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "incomplete"
            assert "missing_fields" in data

    @pytest.mark.asyncio
    async def test_from_text_empty(self, client: AsyncClient) -> None:
        """Empty text → 400."""
        resp = await client.post("/workflow/from-text", json={"text": ""})
        assert resp.status_code == 400
