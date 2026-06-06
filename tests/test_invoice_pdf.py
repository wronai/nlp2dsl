"""Tests for minimal PDF invoice writer."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.invoice_pdf import build_invoice_pdf_bytes, write_invoice_pdf


def test_build_invoice_pdf_starts_with_pdf_header() -> None:
    raw = build_invoice_pdf_bytes(to="a@b.pl", amount=1500, currency="PLN")
    assert raw.startswith(b"%PDF")
    assert b"FAKTURA" in raw
    assert b"1500" in raw
    assert raw.rstrip().endswith(b"%%EOF")


def test_write_invoice_pdf_creates_valid_file(tmp_path: Path) -> None:
    out = tmp_path / "inv.pdf"
    write_invoice_pdf(out, to="x@y.pl", amount="99.5", currency="EUR")
    assert out.is_file()
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"99.5" in data
    assert data.rstrip().endswith(b"%%EOF")
