"""Tests for attachment_validation formatting."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.attachment_validation import (
    build_attachment_validation,
    enrich_chat_response,
    format_attachment_validation,
)
from nlp2dsl_sdk.invoice_pdf import write_invoice_pdf


def test_format_attachment_validation_ok() -> None:
    line = format_attachment_validation(
        {
            "path": ".nlp2dsl/generated/invoices/x.pdf",
            "resolved": "/tmp/x.pdf",
            "status": "ok",
            "issues": [],
        }
    )
    assert line is not None
    assert "[ok]" in line
    assert "x.pdf" in line


def test_enrich_chat_response_from_dsl(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv = ex / ".nlp2dsl" / "generated" / "invoices"
    inv.mkdir(parents=True)
    pdf = inv / "INV-x.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    raw = "/examples/01-invoice/.nlp2dsl/generated/invoices/INV-x.pdf"
    data = {
        "status": "executed",
        "dsl": {
            "steps": [
                {
                    "action": "send_invoice",
                    "config": {"amount": 1500, "to": "a@b.pl", "attachment_path": raw},
                }
            ]
        },
        "execution": {
            "steps": [
                {
                    "action": "send_invoice",
                    "status": "completed",
                    "result": {"attachment_path": raw, "attachment_used": True},
                }
            ]
        },
    }
    av = enrich_chat_response(data)
    assert av["status"] == "ok"
    assert data["attachment_validation"]["status"] == "ok"
    assert data["execution"]["steps"][0]["result"]["attachment_validation"]["status"] == "ok"


def test_build_attachment_validation_rejects_text_pdf(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv = ex / ".nlp2dsl" / "generated" / "invoices"
    inv.mkdir(parents=True)
    pdf = inv / "INV-text.pdf"
    pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    av = build_attachment_validation(
        ".nlp2dsl/generated/invoices/INV-text.pdf",
        action="send_invoice",
        config={"amount": 1500, "to": "a@b.pl"},
    )
    assert av["status"] == "invalid"
    assert any("%PDF" in issue for issue in av["issues"])
