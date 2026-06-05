"""Tests for execution/delegate.py."""

from __future__ import annotations

from app.execution.delegate import (
    delegate_payload,
    execution_backend_for_intent,
    is_delegated_to_mullm,
)


def test_mullm_shell_delegated() -> None:
    assert is_delegated_to_mullm("mullm_shell_task")
    assert execution_backend_for_intent("mullm_shell_task") == "mullm"


def test_invoice_worker_backend() -> None:
    assert execution_backend_for_intent("send_invoice") == "worker"


def test_system_runtime_backend() -> None:
    from app.conversation.doql_context import DoqlCommand, DoqlTaskContext
    from app.conversation.system_map import set_doql_context

    set_doql_context(
        DoqlTaskContext(
            commands=[DoqlCommand(name="system_file_list", runtime="orchestrator:nlp-service")],
        )
    )
    assert execution_backend_for_intent("system_file_list") == "system"
    set_doql_context(None)


def test_delegate_payload_shape() -> None:
    payload = delegate_payload("mullm_shell_task", {"shell_command": "ls"})
    assert payload["backend"] == "mullm"
    assert payload["action"] == "mullm_shell_task"
