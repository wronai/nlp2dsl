"""Tests for pre-execution step validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.conversation.doql_context import DoqlCommand, DoqlTaskContext
from app.conversation.system_map import set_doql_context
from app.validation.step_validator import validate_step_config, validate_workflow_steps


@pytest.fixture(autouse=True)
def _clear_doql() -> None:
    set_doql_context(None)
    yield
    set_doql_context(None)


def test_send_invoice_valid_without_attachment() -> None:
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "klient@firma.pl", "currency": "PLN", "attachment_path": ""},
    )
    assert issues == []


def test_send_invoice_missing_to() -> None:
    issues = validate_step_config("send_invoice", {"amount": 1500})
    assert any("to" in i for i in issues)


def test_send_invoice_invalid_email() -> None:
    issues = validate_step_config("send_invoice", {"amount": 1500, "to": "not-an-email"})
    assert any("to:" in i for i in issues)


def test_attachment_required_blocks_empty_path() -> None:
    ctx = DoqlTaskContext(
        attachment_required=True,
        commands=[DoqlCommand(name="send_invoice", required=["amount", "to"])],
    )
    set_doql_context(ctx)
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": ""},
    )
    assert any("attachment_path" in i for i in issues)


def test_mvp_invoice_file_valid(tmp_path: Path) -> None:
    pdf = tmp_path / "inv.pdf"
    pdf.write_text("FAKTURA\nOdbiorca: a@b.pl\nKwota: 1500.0 PLN\n", encoding="utf-8")
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(pdf)},
    )
    assert issues == []


def test_mvp_invoice_amount_mismatch(tmp_path: Path) -> None:
    pdf = tmp_path / "inv.pdf"
    pdf.write_text("FAKTURA\nOdbiorca: a@b.pl\nKwota: 999.0 PLN\n", encoding="utf-8")
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(pdf)},
    )
    assert any("kwota" in i.lower() for i in issues)


def test_invalid_attachment_content(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_text("not an invoice", encoding="utf-8")
    issues = validate_step_config(
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(bad)},
    )
    assert any("FAKTURA" in i or "PDF" in i for i in issues)


def test_validate_workflow_steps_index() -> None:
    from app.schemas import DSLStep

    failures = validate_workflow_steps(
        [DSLStep(action="send_invoice", config={"amount": 1500, "to": "a@b.pl"})]
    )
    assert failures == []
