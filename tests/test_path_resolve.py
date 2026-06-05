"""Path resolve + strict PDF validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nlp2dsl_sdk.path_resolve import resolve_attachment_path
from nlp2dsl_sdk.step_validation import validate_step_config_from_map
from nlp2dsl_sdk.system_map_ir import CommandSchemaIR, FieldSpec, SystemMapIR


def test_resolve_fixture_relative_path(tmp_path: Path, monkeypatch) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    pdf = fixtures / "faktura-2024.pdf"
    pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(tmp_path))

    resolved = resolve_attachment_path("fixtures/faktura-2024.pdf")
    assert Path(resolved).is_file()
    assert resolved.endswith("faktura-2024.pdf")


def test_mvp_pdf_passes_without_strict(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura.pdf"
    pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    monkeypatch.delenv("NLP2DSL_STRICT_PDF", raising=False)

    ir = SystemMapIR(
        commands=[CommandSchemaIR(name="send_invoice", fields=[FieldSpec(name="amount"), FieldSpec(name="to")])]
    )
    issues = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/faktura.pdf"},
    )
    assert issues == []


def test_strict_pdf_rejects_mvp_text(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura.pdf"
    pdf.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    monkeypatch.setenv("NLP2DSL_STRICT_PDF", "1")

    ir = SystemMapIR(
        commands=[CommandSchemaIR(name="send_invoice", fields=[FieldSpec(name="amount"), FieldSpec(name="to")])]
    )
    issues = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/faktura.pdf"},
    )
    assert any("%PDF" in i for i in issues)
