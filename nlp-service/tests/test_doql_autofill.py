"""Orchestrator integration — DOQL autofill on conversation start."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.orchestrator import start_conversation
from app.store.memory import MemoryConversationStore


SAMPLE_DOQL = """
environment[name="01-invoice"] {
  NLP2DSL_BACKEND_URL: "http://localhost:8010";
}

data {
  send_invoice.amount: 1500;
  send_invoice.to: "klient@firma.pl";
  send_invoice.currency: "PLN";
}

conversation {
  autofill: true;
}
"""


@pytest.fixture(autouse=True)
def _patch_store(monkeypatch, tmp_path: Path) -> Path:
    import app.conversation.orchestrator as conv_orch_mod
    import app.orchestrator as orch_mod

    store = MemoryConversationStore()
    monkeypatch.setattr(conv_orch_mod, "_store", store)
    monkeypatch.setattr(orch_mod, "_store", store)

    doql_path = tmp_path / "environment.doql.less"
    doql_path.write_text(SAMPLE_DOQL, encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_DOQL_CONTEXT", str(doql_path))
    return doql_path


class TestDoqlAutofillConversation:
    @pytest.mark.asyncio
    async def test_start_incomplete_autofilled_to_ready(self) -> None:
        resp = await start_conversation(
            "Wyślij fakturę",
            context_inline={
                "send_invoice.amount": 1500,
                "send_invoice.to": "klient@firma.pl",
                "send_invoice.currency": "PLN",
            },
        )
        assert resp.status == "ready"
        assert resp.dsl is not None
        assert resp.dsl.steps[0].action == "send_invoice"
        assert resp.missing == []
