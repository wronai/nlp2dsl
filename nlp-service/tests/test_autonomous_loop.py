"""Autonomous resolution loop tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.conversation.autonomous_loop import autonomous_resolve_turn
from app.conversation.orchestrator import start_conversation
from app.validation.path_resolve import resolve_attachment_path
from app.store.memory import MemoryConversationStore


SAMPLE_DOQL = """
environment[name="01-invoice"] {}

data {
  send_invoice.amount: 1500;
  send_invoice.to: "klient@firma.pl";
  send_invoice.currency: "PLN";
}

conversation {
  autofill: true;
  sync_auto_execute: false;
}
"""


@pytest.fixture(autouse=True)
def _patch_store(monkeypatch, tmp_path: Path) -> None:
    import app.conversation.orchestrator as conv_orch_mod
    import app.orchestrator as orch_mod

    store = MemoryConversationStore()
    monkeypatch.setattr(conv_orch_mod, "_store", store)
    monkeypatch.setattr(orch_mod, "_store", store)

    doql_path = tmp_path / "environment.doql.less"
    doql_path.write_text(SAMPLE_DOQL, encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_DOQL_CONTEXT", str(doql_path))


@pytest.mark.asyncio
async def test_autonomous_resolves_invoice_to_ready() -> None:
    from app.schemas import ConversationState

    state = ConversationState(id="t1", intent="send_invoice")
    state.history.append({"role": "user", "text": "Wyślij fakturę"})
    state.entities = {}

    result = await autonomous_resolve_turn(state)
    assert result.response is not None
    assert result.response.status == "ready"
    assert result.steps


@pytest.mark.asyncio
async def test_start_conversation_autonomous_ready() -> None:
    resp = await start_conversation("Wyślij fakturę")
    assert resp.status == "ready"
    assert resp.dsl is not None
    assert resp.autonomous_steps or resp.autofill_applied


@pytest.mark.asyncio
async def test_autonomous_rejects_text_pdf_artifact_and_generates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas import ConversationState

    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    registry = ex / ".nlp2dsl" / "registry"
    fixtures.mkdir(parents=True)
    registry.mkdir(parents=True)
    bad_pdf = fixtures / "faktura.pdf"
    bad_pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")

    doql_path = registry / "environment.doql.less"
    doql_path.write_text(
        SAMPLE_DOQL
        + """
capabilities {
  actions: "send_invoice,generate_invoice";
}

artifacts[0] {
  path: "fixtures/faktura.pdf";
  kind: "file";
}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("NLP2DSL_DOQL_CONTEXT", str(doql_path))
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    state = ConversationState(id="t-bad-pdf", intent="send_invoice")
    state.history.append({"role": "user", "text": "Wyślij fakturę"})

    result = await autonomous_resolve_turn(state)

    assert result.response is not None
    assert result.response.status == "ready"
    assert result.response.dsl is not None
    attachment = result.response.dsl.steps[0].config["attachment_path"]
    resolved = Path(resolve_attachment_path(str(attachment), doql_path=doql_path))
    assert resolved != bad_pdf
    data = resolved.read_bytes()
    assert data.startswith(b"%PDF")
    assert data.rstrip().endswith(b"%%EOF")
