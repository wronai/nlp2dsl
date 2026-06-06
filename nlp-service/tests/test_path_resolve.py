"""Tests for attachment path resolution in step validator."""

from __future__ import annotations

from pathlib import Path

from app.validation.invoice_pdf import write_invoice_pdf
from app.validation.path_resolve import resolve_attachment_path
from app.validation.step_validator import validate_step_config


def test_validate_resolves_relative_fixture(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura-2024.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))

    resolved = resolve_attachment_path("fixtures/faktura-2024.pdf")
    assert Path(resolved).is_file()

    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/faktura-2024.pdf"},
    )
    assert issues == []
