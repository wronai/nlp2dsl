"""Tests for backend chat auto-execute routing helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.routers import chat


class DummyWorkflowResult:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
async def test_ready_chat_auto_executes_worker_workflow() -> None:
    wf_payload = {
        "workflow_id": "wf-chat-1",
        "name": "invoice_chat",
        "status": "completed",
        "steps": [],
    }
    result = {
        "status": "ready",
        "auto_execute": True,
        "message": "Gotowe. Wyślij 'uruchom' aby wykonać.",
        "dsl": {
            "name": "invoice_chat",
            "trigger": "manual",
            "steps": [
                {
                    "action": "send_invoice",
                    "config": {"to": "client@example.com", "amount": 1500},
                }
            ],
        },
    }

    run_workflow = AsyncMock(return_value=DummyWorkflowResult(wf_payload))
    with patch("app.routers.chat.run_workflow", run_workflow):
        executed = await chat._maybe_auto_execute(result, {"text": "", "sync_auto_execute": True})

    assert executed["status"] == "executed"
    assert executed["execution_backend"] == "worker"
    assert executed["execution"] == wf_payload
    assert executed["message"] == "Gotowe. Wykonano automatycznie (sync_auto_execute)."

    req = run_workflow.await_args.args[0]
    assert req.name == "invoice_chat"
    assert req.trigger == "manual"
    assert req.steps[0].action == "send_invoice"
    assert req.steps[0].config == {"to": "client@example.com", "amount": 1500}


@pytest.mark.asyncio
async def test_ready_chat_delegates_mullm_steps_without_worker_execution() -> None:
    result = {
        "status": "ready",
        "dsl": {
            "name": "list_files",
            "steps": [
                {
                    "action": "mullm_shell_task",
                    "config": {"shell_command": "ls -la"},
                }
            ],
        },
    }

    run_workflow = AsyncMock()
    with patch("app.routers.chat.run_workflow", run_workflow):
        delegated = await chat._maybe_auto_execute(result, {"text": "uruchom"})

    run_workflow.assert_not_awaited()
    assert delegated["status"] == "ready"
    assert delegated["execution_backend"] == "mullm"
    assert delegated["execution"]["backend"] == "mullm"
    assert delegated["execution"]["steps"] == result["dsl"]["steps"]


@pytest.mark.asyncio
async def test_ready_chat_rejects_invalid_dsl_contract_before_execution() -> None:
    result = {
        "status": "ready",
        "auto_execute": True,
        "dsl": {
            "name": "broken_chat",
            "steps": [{"config": {"amount": 1500}}],
        },
    }

    run_workflow = AsyncMock()
    with patch("app.routers.chat.run_workflow", run_workflow):
        rejected = await chat._maybe_auto_execute(result, {"text": "uruchom"})

    run_workflow.assert_not_awaited()
    assert rejected["status"] == "validation_failed"
    assert rejected["missing_fields"] == ["steps.0.action"]
    assert rejected["validation_issues"][0]["code"] == "workflow.missing_action"
    assert "Workflow nie został wykonany" in rejected["message"]
