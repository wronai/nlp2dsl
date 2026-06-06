"""
Tests for backend/app/workflow.py — workflow API endpoints.

Uses httpx.AsyncClient with ASGI transport (no real server needed).
Mocks external HTTP calls to worker and nlp-service.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, Response

from app.idempotency import idempotency_store

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

    @staticmethod
    def _sample_nlp_actions() -> dict:
        return {
            "send_invoice": {
                "description": "Generuje i wysyła fakturę",
                "required": ["amount", "to"],
                "optional": ["currency"],
                "aliases": [],
            },
            "send_email": {
                "description": "Wysyła e-mail",
                "required": ["to"],
                "optional": ["subject", "body"],
                "aliases": [],
            },
        }

    @pytest.mark.asyncio
    async def test_workflow_actions(self, client: AsyncClient) -> None:
        """GET /workflow/actions → list of available actions."""
        mock_resp = MagicMock(spec=Response)
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._sample_nlp_actions()

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.get("/workflow/actions")
        assert resp.status_code == 200
        actions = resp.json()
        assert isinstance(actions, list)
        assert len(actions) > 0
        for action in actions:
            assert "name" in action
            assert "description" in action

    @pytest.mark.asyncio
    async def test_workflow_actions_contains_invoice(self, client: AsyncClient) -> None:
        """Actions list includes send_invoice."""
        mock_resp = MagicMock(spec=Response)
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._sample_nlp_actions()

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

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
                    "steps": [
                        {
                            "action": "send_invoice",
                            "config": {"amount": 1500, "to": "a@b.pl"},
                        }
                    ],
                },
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_start_workflow(self, client: AsyncClient) -> None:
        """POST /workflow/start → returns running snapshot immediately."""
        with patch("app.engine.asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task

            resp = await client.post(
                "/workflow/start",
                json={
                    "name": "background_workflow",
                    "steps": [
                        {"action": "send_invoice", "config": {"to": "x@y.pl", "amount": 100}},
                    ],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "running"
            assert data["workflow_id"]
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_workflow(self, client: AsyncClient) -> None:
        """GET /workflow/stream/{workflow_id} → snapshot + terminal SSE events."""
        mock_resp = _mock_worker_response(
            json_data={"step_id": "step1", "status": "completed", "result": {"invoice_id": "INV-001"}}
        )

        with patch("app.engine.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            start_resp = await client.post(
                "/workflow/start",
                json={
                    "name": "stream_workflow",
                    "steps": [
                        {"action": "send_invoice", "config": {"to": "x@y.pl", "amount": 100}},
                    ],
                },
            )
            workflow_id = start_resp.json()["workflow_id"]

            await asyncio.sleep(0.01)

            resp = await client.get(f"/workflow/stream/{workflow_id}")
            assert resp.status_code == 200
            body = resp.text
            assert "event: snapshot" in body
            assert "event: workflow_completed" in body or "event: workflow_failed" in body


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

    @pytest.mark.asyncio
    async def test_from_text_rejects_invalid_workflow_contract(self, client: AsyncClient) -> None:
        """Complete NLP response with broken workflow is reported, not executed."""
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "status": "complete",
            "workflow": {
                "name": "broken_workflow",
                "steps": [{"config": {"amount": 1500}}],
            },
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient, patch(
            "app.workflow_execute.run_workflow", AsyncMock()
        ) as run_workflow:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/from-text",
                json={"text": "Wyślij fakturę", "execute": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validation_failed"
        assert data["missing_fields"] == ["steps.0.action"]
        assert data["validation_issues"][0]["code"] == "workflow.missing_action"
        run_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_from_text_replays_with_idempotency_key(self, client: AsyncClient) -> None:
        await idempotency_store.clear()
        workflow = {
            "name": "auto_send_invoice",
            "trigger": "manual",
            "steps": [{"action": "send_invoice", "config": {"amount": 500, "to": "test@firma.pl"}}],
        }
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {"status": "complete", "workflow": workflow}

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "workflow_id": "wf-from-text",
            "name": "auto_send_invoice",
            "status": "completed",
            "steps": [],
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient, patch(
            "app.workflow_execute.run_workflow", AsyncMock(return_value=mock_result)
        ) as run_workflow:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            first = await client.post(
                "/workflow/from-text",
                json={"text": "Wyślij fakturę", "execute": True, "idempotency_key": "idem-from-text"},
            )
            second = await client.post(
                "/workflow/from-text",
                json={"text": "Wyślij fakturę", "execute": True, "idempotency_key": "idem-from-text"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["idempotent_replay"] is False
        assert second.json()["idempotent_replay"] is True
        assert second.json()["result"]["workflow_id"] == "wf-from-text"
        run_workflow.assert_awaited_once()


# ── Plan ─────────────────────────────────────────────────────────


class TestWorkflowPlan:
    """POST /workflow/plan endpoint."""

    @pytest.mark.asyncio
    async def test_plan_complete_adds_validation_report(self, client: AsyncClient) -> None:
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "stage": "plan",
            "status": "complete",
            "workflow": {
                "name": "auto_send_invoice",
                "trigger": "manual",
                "steps": [
                    {
                        "action": "send_invoice",
                        "config": {"amount": 1500, "to": "a@b.pl"},
                    }
                ],
            },
            "missing_fields": [],
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/plan",
                json={"text": "Wyślij fakturę na 1500 PLN do a@b.pl"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        assert data["validation"]["status"] == "complete"
        assert data["validation"]["issues"] == []
        assert data["validation"]["missing_fields"] == []

    @pytest.mark.asyncio
    async def test_plan_validation_failure_is_reported(self, client: AsyncClient) -> None:
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "stage": "plan",
            "status": "complete",
            "workflow": {
                "name": "broken_workflow",
                "steps": [{"config": {"amount": 1500}}],
            },
            "missing_fields": [],
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/plan",
                json={"text": "Wyślij fakturę"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validation_failed"
        assert data["validation"]["missing_fields"] == ["steps.0.action"]


# ── Validate ─────────────────────────────────────────────────────


class TestWorkflowValidate:
    """POST /workflow/validate endpoint."""

    @pytest.mark.asyncio
    async def test_validate_with_check_policy_blocks_email_domain(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/workflow/validate",
            json={
                "workflow": {
                    "name": "policy_demo",
                    "steps": [
                        {
                            "action": "send_invoice",
                            "config": {"to": "x@evil.example", "amount": 100},
                        }
                    ],
                },
                "check_policy": True,
                "policy": {"allowed_email_domains": ["company.com"]},
                "skip_access_check": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "blocked"
        assert data["can_execute"] is False
        assert any(i.get("code") == "policy.recipient_not_allowed" for i in data.get("policy_issues", []))

    @pytest.mark.asyncio
    async def test_validate_complete_workflow(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/workflow/validate",
            json={
                "workflow": {
                    "name": "auto_send_invoice",
                    "trigger": "manual",
                    "steps": [
                        {
                            "action": "send_invoice",
                            "config": {"amount": 1500, "to": "a@b.pl"},
                        }
                    ],
                }
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "validate"
        assert data["status"] == "complete"
        assert data["can_execute"] is True
        assert data["issues"] == []

    @pytest.mark.asyncio
    async def test_validate_invalid_workflow(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/workflow/validate",
            json={"workflow": {"name": "broken", "steps": [{"config": {"amount": 1500}}]}},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validation_failed"
        assert data["can_execute"] is False
        assert data["missing_fields"] == ["steps.0.action"]
        assert data["issues"][0]["code"] == "workflow.missing_action"

    @pytest.mark.asyncio
    async def test_validate_requires_workflow(self, client: AsyncClient) -> None:
        resp = await client.post("/workflow/validate", json={})
        assert resp.status_code == 400


# ── Execute ──────────────────────────────────────────────────────


class TestWorkflowExecute:
    """POST /workflow/execute endpoint."""

    @staticmethod
    def _valid_workflow() -> dict:
        return {
            "name": "auto_send_invoice",
            "trigger": "manual",
            "steps": [
                {
                    "action": "send_invoice",
                    "config": {"amount": 1500, "to": "a@b.pl"},
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_execute_dry_run_validates_without_running(self, client: AsyncClient) -> None:
        with patch("app.workflow_execute.run_workflow", AsyncMock()) as run_workflow:
            resp = await client.post(
                "/workflow/execute",
                json={"workflow": self._valid_workflow(), "dry_run": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "execute"
        assert data["status"] == "ready"
        assert data["can_execute"] is True
        assert data["dry_run"] is True
        run_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_invalid_workflow(self, client: AsyncClient) -> None:
        with patch("app.workflow_execute.run_workflow", AsyncMock()) as run_workflow:
            resp = await client.post(
                "/workflow/execute",
                json={"workflow": {"name": "broken", "steps": [{"config": {}}]}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validation_failed"
        assert data["validation"]["missing_fields"] == ["steps.0.action"]
        run_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_clear_idempotency_store_endpoint(self, client: AsyncClient) -> None:
        await idempotency_store.clear()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "workflow_id": "wf-clear",
            "name": "auto_send_invoice",
            "status": "completed",
            "steps": [],
        }
        with patch("app.workflow_execute.run_workflow", AsyncMock(return_value=mock_result)):
            await client.post(
                "/workflow/execute",
                json={"workflow": self._valid_workflow(), "idempotency_key": "idem-clear"},
            )
        replay = await client.post(
            "/workflow/execute",
            json={"workflow": self._valid_workflow(), "idempotency_key": "idem-clear"},
        )
        assert replay.json().get("idempotent_replay") is True

        cleared = await client.post("/workflow/idempotency/clear")
        assert cleared.status_code == 200
        assert cleared.json()["status"] == "cleared"

        fresh = await client.post(
            "/workflow/execute",
            json={"workflow": self._valid_workflow(), "idempotency_key": "idem-clear"},
        )
        assert fresh.status_code == 200
        assert fresh.json().get("idempotent_replay") is not True

    @pytest.mark.asyncio
    async def test_execute_runs_valid_workflow(self, client: AsyncClient) -> None:
        await idempotency_store.clear()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "workflow_id": "wf-1",
            "name": "auto_send_invoice",
            "status": "completed",
            "steps": [],
        }

        with patch("app.workflow_execute.run_workflow", AsyncMock(return_value=mock_result)) as run_workflow:
            resp = await client.post(
                "/workflow/execute",
                json={
                    "workflow": self._valid_workflow(),
                    "idempotency_key": "idem-1",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "executed"
        assert data["result"]["workflow_id"] == "wf-1"
        assert data["idempotency_key"] == "idem-1"
        run_workflow.assert_awaited_once()
        mock_result.model_dump.assert_called_once_with(mode="json")

    @pytest.mark.asyncio
    async def test_execute_replays_same_idempotency_key(self, client: AsyncClient) -> None:
        await idempotency_store.clear()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "workflow_id": "wf-repeat",
            "name": "auto_send_invoice",
            "status": "completed",
            "steps": [],
        }

        with patch("app.workflow_execute.run_workflow", AsyncMock(return_value=mock_result)) as run_workflow:
            first = await client.post(
                "/workflow/execute",
                json={
                    "workflow": self._valid_workflow(),
                    "idempotency_key": "idem-repeat",
                },
            )
            second = await client.post(
                "/workflow/execute",
                json={
                    "workflow": self._valid_workflow(),
                    "idempotency_key": "idem-repeat",
                },
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["idempotent_replay"] is False
        assert second.json()["idempotent_replay"] is True
        assert second.json()["result"]["workflow_id"] == "wf-repeat"
        run_workflow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_rejects_reused_key_for_different_workflow(self, client: AsyncClient) -> None:
        await idempotency_store.clear()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "workflow_id": "wf-conflict",
            "name": "auto_send_invoice",
            "status": "completed",
            "steps": [],
        }
        changed = self._valid_workflow()
        changed["steps"][0]["config"]["amount"] = 2000

        with patch("app.workflow_execute.run_workflow", AsyncMock(return_value=mock_result)) as run_workflow:
            first = await client.post(
                "/workflow/execute",
                json={
                    "workflow": self._valid_workflow(),
                    "idempotency_key": "idem-conflict",
                },
            )
            second = await client.post(
                "/workflow/execute",
                json={
                    "workflow": changed,
                    "idempotency_key": "idem-conflict",
                },
            )

        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json()["detail"]["error"] == "idempotency_key_conflict"
        run_workflow.assert_awaited_once()


# ── Simulate ─────────────────────────────────────────────────────


class TestWorkflowSimulate:
    """POST /workflow/simulate endpoint."""

    def _valid_workflow(self) -> dict:
        return {
            "name": "full_report_flow",
            "trigger": "weekly",
            "steps": [
                {"action": "generate_report", "config": {"report_type": "sales", "format": "pdf"}},
                {"action": "send_email", "config": {"to": "a@b.pl", "subject": "x", "body": "y"}},
                {"action": "notify_slack", "config": {"channel": "#sales", "message": "ok"}},
            ],
        }

    @pytest.mark.asyncio
    async def test_simulate_workflow_dsl_without_execution(self, client: AsyncClient) -> None:
        with patch("app.workflow_execute.run_workflow", AsyncMock()) as run_workflow:
            resp = await client.post("/workflow/simulate", json={"workflow": self._valid_workflow()})

        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "simulate"
        assert data["status"] == "ready"
        assert data["step_count"] == 3
        assert data["side_effect_count"] == 2
        assert data["can_execute"] is True
        run_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_simulate_from_text_composes_plan(self, client: AsyncClient) -> None:
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "status": "complete",
            "workflow": self._valid_workflow(),
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient, patch(
            "app.workflow_execute.run_workflow", AsyncMock()
        ) as run_workflow:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/simulate",
                json={"text": "raport PDF email slack", "mode": "rules"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "simulate"
        assert data["step_count"] == 3
        run_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_from_text_simulate_flag(self, client: AsyncClient) -> None:
        mock_nlp_resp = MagicMock(spec=Response)
        mock_nlp_resp.status_code = 200
        mock_nlp_resp.is_success = True
        mock_nlp_resp.headers = {"content-type": "application/json"}
        mock_nlp_resp.json.return_value = {
            "status": "complete",
            "workflow": self._valid_workflow(),
        }

        with patch("app.routers.workflow.AsyncClient") as MockClient, patch(
            "app.workflow_execute.run_workflow", AsyncMock()
        ) as run_workflow:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_nlp_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            resp = await client.post(
                "/workflow/from-text",
                json={"text": "raport PDF email slack", "simulate": True, "mode": "rules"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "simulate"
        assert "dsl" in data
        run_workflow.assert_not_awaited()
