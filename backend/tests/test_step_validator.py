"""Backend step validation before worker dispatch."""

from __future__ import annotations

from pathlib import Path

from app.step_validator import validate_step_config


def test_send_invoice_ok() -> None:
    assert validate_step_config("send_invoice", {"amount": 1500, "to": "a@b.pl"}) == []


def test_missing_attachment_file() -> None:
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "/no/such/file.pdf"},
    )
    assert any("nie istnieje" in i for i in issues)


def test_mvp_invoice_ok(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    path.write_text("FAKTURA\nKwota: 1500.0 PLN\n", encoding="utf-8")
    assert (
        validate_step_config(
            "send_invoice",
            {"amount": 1500, "to": "a@b.pl", "attachment_path": str(path)},
        )
        == []
    )
