"""Tests for Docker /examples mount path resolution."""

from __future__ import annotations

from pathlib import Path

from app.validation.invoice_pdf import write_invoice_pdf
from app.validation.attachment_validation import build_attachment_validation
from app.validation.path_resolve import resolve_attachment_path


def test_resolve_examples_mount_path_on_host(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv_dir = ex / ".nlp2dsl" / "generated" / "invoices"
    inv_dir.mkdir(parents=True)
    pdf = inv_dir / "INV-test-1500-PLN.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")

    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    portable = "/examples/01-invoice/.nlp2dsl/generated/invoices/INV-test-1500-PLN.pdf"
    resolved = resolve_attachment_path(portable)
    assert Path(resolved).is_file()
    assert resolved.endswith("INV-test-1500-PLN.pdf")


def test_build_attachment_validation_ok(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv_dir = ex / ".nlp2dsl" / "generated" / "invoices"
    inv_dir.mkdir(parents=True)
    pdf = inv_dir / "INV-test-1500-PLN.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")

    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    raw = ".nlp2dsl/generated/invoices/INV-test-1500-PLN.pdf"
    av = build_attachment_validation(
        raw,
        action="send_invoice",
        config={"amount": 1500, "to": "a@b.pl", "attachment_path": raw},
    )
    assert av["status"] == "ok"
    assert Path(av["resolved"]).is_file()
    assert av["issues"] == []


def test_build_attachment_validation_rejects_text_pdf(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv_dir = ex / ".nlp2dsl" / "generated" / "invoices"
    inv_dir.mkdir(parents=True)
    pdf = inv_dir / "INV-text.pdf"
    pdf.write_text("FAKTURA\nOdbiorca: a@b.pl\nKwota: 1500.0 PLN\n", encoding="utf-8")

    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    raw = ".nlp2dsl/generated/invoices/INV-text.pdf"
    av = build_attachment_validation(
        raw,
        action="send_invoice",
        config={"amount": 1500, "to": "a@b.pl", "attachment_path": raw},
    )
    assert av["status"] == "invalid"
    assert any("%PDF" in issue for issue in av["issues"])
