"""Tests for nlp-service DOQL registry patch refresh."""

from __future__ import annotations

from pathlib import Path

from app.conversation.doql_context import load_doql_context
from app.conversation.doql_registry import _patch_doql_file, refresh_registry_for_state
from app.schemas import ConversationState


SAMPLE = """
environment[name="01-invoice"] {}

data {
  send_invoice.amount: 1500;
}

runtimes[0] {
  id: "executor:worker";
  kind: "worker";
  status: "available";
}

commands[0] {
  name: "send_invoice";
  runtime: "executor:worker";
  required: "amount,to";
}

conversation {
  autofill: true;
}
"""


def test_patch_doql_data_and_history(tmp_path: Path) -> None:
    path = tmp_path / "environment.doql.less"
    path.write_text(SAMPLE, encoding="utf-8")
    _patch_doql_file(
        path,
        data_patch={"send_invoice.to": "a@b.pl", "to": "a@b.pl"},
        history_patch={"last_phase": "test", "last_intent": "send_invoice"},
    )
    ctx = load_doql_context(path)
    assert ctx.data["send_invoice.to"] == "a@b.pl"
    assert ctx.workflow_history["last_phase"] == "test"
    text = path.read_text()
    assert "runtimes[0]" in text
    assert 'runtime: "executor:worker"' in text


def test_refresh_registry_for_state(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "environment.doql.less"
    path.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_DOQL_CONTEXT", str(path))

    state = ConversationState(id="conv1", intent="send_invoice")
    state.entities = {"amount": 1800, "to": "x@y.pl"}

    out = refresh_registry_for_state(state, phase="dsl_ready")
    assert out == path
    ctx = load_doql_context(path)
    assert ctx.data["send_invoice.amount"] == 1800
