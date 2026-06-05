"""Tests for DOQL context parsing and autofill."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.conversation.doql_context import (
    autofill_entities,
    load_doql_context,
    merge_inline_context,
)


SAMPLE_DOQL = """
// DOQL task context — 01-invoice
// generated: 2026-06-05T12:00:00+00:00

environment[name="01-invoice"] {
  NLP2DSL_BACKEND_URL: "http://localhost:8010";
}

data {
  send_invoice.amount: 1500;
  send_invoice.to: "klient@firma.pl";
  send_invoice.currency: "PLN";
}

artifacts[0] {
  path: "fixtures/invoice-request.txt";
  kind: "metadata";
  to: "klient@firma.pl";
  amount: 1500;
}

conversation {
  autofill: true;
  sync_auto_execute: false;
}
"""


def test_load_doql_context(tmp_path: Path) -> None:
    path = tmp_path / "environment.doql.less"
    path.write_text(SAMPLE_DOQL, encoding="utf-8")
    ctx = load_doql_context(path)
    assert ctx.example_name == "01-invoice"
    assert ctx.data["send_invoice.amount"] == 1500
    assert ctx.data["send_invoice.to"] == "klient@firma.pl"
    assert ctx.autofill is True
    assert len(ctx.artifacts) == 1


def test_autofill_entities_from_data() -> None:
    from app.conversation.doql_context import DoqlTaskContext

    ctx = DoqlTaskContext(
        data={
            "send_invoice.amount": 1500.0,
            "send_invoice.to": "klient@firma.pl",
        },
        autofill=True,
    )
    entities = {"intent": "send_invoice"}
    missing = ["send_invoice.amount", "send_invoice.to"]
    updated, filled = autofill_entities(entities, missing, ctx, intent="send_invoice")
    assert updated["amount"] == 1500.0
    assert updated["to"] == "klient@firma.pl"
    assert len(filled) == 2


def test_merge_inline_attachment_path() -> None:
    from app.conversation.doql_context import DoqlTaskContext

    ctx = DoqlTaskContext(autofill=True)
    merged = merge_inline_context(ctx, {"attachmentPath": "/tmp/faktura.pdf"})
    assert merged.data["attachment_path"] == "/tmp/faktura.pdf"


def test_merge_inline_dotted_action_fields() -> None:
    from app.conversation.doql_context import DoqlTaskContext

    ctx = DoqlTaskContext(autofill=True)
    merged = merge_inline_context(
        ctx,
        {
            "send_invoice.amount": 1500,
            "send_invoice.to": "klient@firma.pl",
            "conversation.autofill": True,
        },
    )
    assert merged.data["send_invoice.amount"] == 1500
    assert merged.data["amount"] == 1500
    assert merged.data["to"] == "klient@firma.pl"
    assert merged.autofill is True


def test_merge_inline_entities_dotted_keys() -> None:
    from app.conversation.orchestrator import _merge_inline_entities
    from app.schemas import ConversationState

    state = ConversationState(id="test")
    _merge_inline_entities(
        state,
        {
            "send_invoice.amount": 1500,
            "send_invoice.to": "klient@firma.pl",
            "conversation.autofill": True,
        },
    )
    assert state.entities["amount"] == 1500
    assert state.entities["to"] == "klient@firma.pl"
    assert "conversation.autofill" not in state.entities


def test_load_doql_runtimes(tmp_path: Path) -> None:
    doql = """
environment[name="01-invoice"] {}

runtimes[0] {
  id: "executor:worker";
  kind: "worker";
  status: "available";
}

runtimes[1] {
  id: "delegate:mullm";
  kind: "external";
  status: "unavailable";
}
"""
    path = tmp_path / "environment.doql.less"
    path.write_text(doql, encoding="utf-8")
    ctx = load_doql_context(path)
    assert len(ctx.runtimes) == 2
    assert ctx.runtimes[0].id == "executor:worker"


def test_runtime_unavailable_message() -> None:
    from app.conversation.doql_context import DoqlRuntime, DoqlTaskContext
    from app.conversation.runtime_gate import runtime_unavailable_message

    ctx = DoqlTaskContext(
        runtimes=[
            DoqlRuntime(id="delegate:mullm", status="unavailable"),
        ]
    )
    msg = runtime_unavailable_message(ctx, "mullm_shell_task")
    assert msg is not None
    assert "delegate:mullm" in msg
    assert runtime_unavailable_message(ctx, "send_invoice") is None
