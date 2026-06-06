"""Attachment-required conversation with DOQL autofill."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.validation.invoice_pdf import write_invoice_pdf
from app.orchestrator import continue_conversation, start_conversation
from app.store.memory import MemoryConversationStore


ATTACHMENT_DOQL = """
environment[name="01-invoice"] {}

data {
  send_invoice.amount: 1500;
  send_invoice.to: "klient@firma.pl";
  send_invoice.currency: "PLN";
}

capabilities {
  actions: "send_invoice,generate_invoice";
}

conversation {
  autofill: true;
  attachment_required: true;
  generate_invoice_if_missing: false;
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
    doql_path.write_text(ATTACHMENT_DOQL, encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_DOQL_CONTEXT", str(doql_path))


class TestAttachmentConversation:
    @pytest.mark.asyncio
    async def test_incomplete_then_attachment_inline(self, tmp_path: Path) -> None:
        resp1 = await start_conversation(
            "Wyślij fakturę do klient@firma.pl",
            context_inline={
                "send_invoice.amount": 1500,
                "send_invoice.to": "klient@firma.pl",
                "attachment_required": True,
                "generate_invoice_if_missing": False,
            },
        )
        assert resp1.status == "in_progress"
        assert resp1.missing
        assert any("attachment" in m for m in resp1.missing)

        pdf = tmp_path / "faktura.pdf"
        write_invoice_pdf(pdf, to="klient@firma.pl", amount=1500, currency="PLN")
        resp2 = await continue_conversation(
            resp1.conversation_id,
            "Plik faktury: faktura.pdf",
            context_inline={"attachmentPath": str(pdf)},
        )
        assert resp2.status == "ready"
        assert resp2.dsl is not None
        cfg = resp2.dsl.steps[0].config
        assert cfg.get("attachment_path")
