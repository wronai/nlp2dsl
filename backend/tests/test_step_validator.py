"""Backend step validation before worker dispatch."""

from __future__ import annotations

from pathlib import Path

from app.step_validator import validate_step_config


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
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "/no/such/file.pdf"},
    )
    assert any("nie istnieje" in i for i in issues)


def test_pdf_invoice_ok(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    _write_test_pdf(path, amount=1500)
    assert (
        validate_step_config(
            "send_invoice",
            {"amount": 1500, "to": "a@b.pl", "attachment_path": str(path)},
        )
        == []
    )


def test_text_pdf_rejected(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    path.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(path)},
    )
    assert any("%PDF" in issue for issue in issues)
