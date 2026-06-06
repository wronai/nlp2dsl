"""Path resolve + strict PDF validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nlp2dsl_sdk.path_resolve import resolve_attachment_path
from nlp2dsl_sdk.invoice_pdf import write_invoice_pdf
from nlp2dsl_sdk.step_validation import validate_step_config_from_map
from nlp2dsl_sdk.system_map_ir import CommandSchemaIR, FieldSpec, SystemMapIR


def test_resolve_fixture_relative_path(tmp_path: Path, monkeypatch) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    pdf = fixtures / "faktura-2024.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(tmp_path))

    resolved = resolve_attachment_path("fixtures/faktura-2024.pdf")
    assert Path(resolved).is_file()
    assert resolved.endswith("faktura-2024.pdf")


def test_resolve_examples_mount_portable_path(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    inv = ex / ".nlp2dsl" / "generated" / "invoices"
    inv.mkdir(parents=True)
    pdf = inv / "INV-x.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    resolved = resolve_attachment_path(
        "/examples/01-invoice/.nlp2dsl/generated/invoices/INV-x.pdf"
    )
    assert Path(resolved).is_file()


def test_pdf_attachment_passes_with_valid_pdf(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    ir = SystemMapIR(
        commands=[CommandSchemaIR(name="send_invoice", fields=[FieldSpec(name="amount"), FieldSpec(name="to")])]
    )
    issues = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/faktura.pdf"},
    )
    assert issues == []


def test_pdf_attachment_rejects_text_file(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura.pdf"
    pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    ir = SystemMapIR(
        commands=[CommandSchemaIR(name="send_invoice", fields=[FieldSpec(name="amount"), FieldSpec(name="to")])]
    )
    issues = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/faktura.pdf"},
    )
    assert any("%PDF" in i for i in issues)
