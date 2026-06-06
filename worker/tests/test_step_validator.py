"""Worker step validation — SDK pipeline adapter (B1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from path_resolve import resolve_worker_attachment_path
from step_validator import validate_step_config


def _write_test_pdf(path: Path, *, amount: int | float = 1500) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        + f"Kwota: {amount} PLN\n".encode("ascii")
        + b"%%EOF\n"
    )


def test_send_invoice_ok() -> None:
    assert validate_step_config("send_invoice", {"amount": 1500, "to": "a@b.pl"}) == []


def test_missing_attachment_file() -> None:
    from nlp2dsl_sdk.validation.issue import Phase

    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "/no/such/file.pdf"},
        phase=Phase.POST_EXECUTE,
    )
    assert any("nie istnieje" in i for i in issues)


def test_pdf_invoice_ok(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    _write_test_pdf(path, amount=1500)
    from nlp2dsl_sdk.validation.issue import Phase

    assert (
        validate_step_config(
            "send_invoice",
            {"amount": 1500, "to": "a@b.pl", "attachment_path": str(path)},
            phase=Phase.POST_EXECUTE,
        )
        == []
    )


def test_text_pdf_rejected(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    path.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    from nlp2dsl_sdk.validation.issue import Phase

    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(path)},
        phase=Phase.POST_EXECUTE,
    )
    assert any("%PDF" in issue for issue in issues)


def test_resolve_worker_attachment_path_prefers_example_dir(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "invoice.pdf"
    _write_test_pdf(fixture)
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(tmp_path))
    resolved = resolve_worker_attachment_path("invoice.pdf")
    assert resolved == str(fixture.resolve())
