"""Tests for ProcessAgent, system map, and runtime-aware delegate."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.conversation.doql_context import DoqlCommand, DoqlProcessPolicy, DoqlRuntime, DoqlTaskContext, load_doql_context
from app.conversation.process_agent import preflight_turn
from app.conversation.system_map import required_fields_for_action, set_doql_context
from app.dsl.mapper import map_to_dsl
from app.execution.delegate import execution_backend_for_intent, execution_backend_for_runtime
from app.routing import IntentDecision
from app.schemas import ConversationState, NLPEntities, NLPIntent, NLPResult


def test_load_doql_commands(tmp_path: Path) -> None:
    doql = """
commands[0] {
  name: "send_invoice";
  required: "amount,to";
  optional: "currency";
  runtime: "executor:worker";
}
"""
    path = tmp_path / "environment.doql.less"
    path.write_text(doql, encoding="utf-8")
    ctx = load_doql_context(path)
    assert len(ctx.commands) == 1
    assert ctx.commands[0].runtime == "executor:worker"
    assert ctx.required_fields_for("send_invoice") == ["amount", "to"]


def test_mapper_uses_doql_required_fields() -> None:
    ctx = DoqlTaskContext(
        commands=[
            DoqlCommand(name="send_invoice", required=["amount", "to"], runtime="executor:worker"),
        ]
    )
    set_doql_context(ctx)
    nlp = NLPResult(
        intent=NLPIntent(intent="send_invoice", confidence=1.0),
        entities=NLPEntities(amount=100),
        raw_text="faktura",
    )
    dialog = map_to_dsl(nlp)
    assert dialog.status == "incomplete"
    assert "send_invoice.to" in (dialog.missing_fields or [])
    set_doql_context(None)


def test_execution_backend_for_runtime() -> None:
    assert execution_backend_for_runtime("executor:worker") == "worker"
    assert execution_backend_for_runtime("delegate:mullm") == "mullm"
    assert execution_backend_for_runtime("orchestrator:nlp-service") == "system"


def test_execution_backend_from_doql_map() -> None:
    ctx = DoqlTaskContext(
        commands=[DoqlCommand(name="send_invoice", runtime="executor:worker")],
        runtimes=[DoqlRuntime(id="executor:worker", status="available")],
    )
    set_doql_context(ctx)
    assert execution_backend_for_intent("send_invoice") == "worker"
    ctx.commands[0].runtime = "delegate:mullm"
    assert execution_backend_for_intent("send_invoice") == "mullm"
    set_doql_context(None)


@pytest.mark.asyncio
async def test_preflight_blocks_unavailable_runtime() -> None:
    ctx = DoqlTaskContext(
        runtimes=[DoqlRuntime(id="delegate:mullm", status="unavailable")],
    )
    state = ConversationState(id="test123")
    state.intent = "mullm_shell_task"
    state.doql_inline = {"autofill": True}

    decision = IntentDecision(
        action="mullm_shell_task",
        intent="mullm_shell_task",
        source="test",
        confidence=1.0,
        authorized=True,
    )

    with patch("app.conversation.process_agent.load_context_for_state", return_value=ctx):
        with patch("app.conversation.process_agent.sync_autofill_from_doql", new_callable=AsyncMock):
            resp = await preflight_turn(state, decision)

    assert resp is not None
    assert resp.status == "blocked"
    assert "delegate:mullm" in resp.message


@pytest.mark.asyncio
async def test_preflight_blocks_process_scope_deny() -> None:
    ctx = DoqlTaskContext(
        runtimes=[DoqlRuntime(id="delegate:mullm", status="available")],
        process=DoqlProcessPolicy(deny_resource_areas=["mullm:rag"]),
    )
    state = ConversationState(id="scope1")
    state.intent = "mullm_list_files"

    decision = IntentDecision(
        action="mullm_list_files",
        intent="mullm_list_files",
        source="test",
        confidence=1.0,
        authorized=True,
        resource_area="mullm:rag",
    )

    with patch("app.conversation.process_agent.load_context_for_state", return_value=ctx):
        with patch("app.conversation.process_agent.sync_autofill_from_doql", new_callable=AsyncMock):
            resp = await preflight_turn(state, decision)

    assert resp is not None
    assert resp.status == "blocked"
    assert "process_access" in resp.message or "mullm:rag" in resp.message


@pytest.mark.asyncio
async def test_preflight_blocks_intract_clarification() -> None:
    ctx = DoqlTaskContext(
        process=DoqlProcessPolicy(
            intract_enforce_clarification=True,
            nlp_confidence_min=0.5,
        ),
    )
    state = ConversationState(id="clarify1")
    state.intent = "unknown"

    decision = IntentDecision(
        action="unknown",
        intent="unknown",
        source="test",
        confidence=0.3,
        authorized=True,
    )

    with patch("app.conversation.process_agent.load_context_for_state", return_value=ctx):
        with patch("app.conversation.process_agent.sync_autofill_from_doql", new_callable=AsyncMock):
            resp = await preflight_turn(state, decision)

    assert resp is not None
    assert resp.status == "blocked"
    assert "doprecyzowania" in resp.message


def test_required_fields_for_action_helper() -> None:
    set_doql_context(
        DoqlTaskContext(commands=[DoqlCommand(name="send_email", required=["to"])])
    )
    assert required_fields_for_action("send_email") == ["to"]
    set_doql_context(None)
