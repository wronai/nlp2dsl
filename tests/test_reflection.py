"""Tests for reflection model (target plan vs current state)."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.reflection import (
    ReflectionReport,
    build_target_plan,
    format_reflection_summary,
    reflect,
    reflect_from_chat_turn,
)
from nlp2dsl_sdk.invoice_pdf import write_invoice_pdf
from nlp2dsl_sdk.system_map_ir import (
    CommandSchemaIR,
    ConversationPolicyIR,
    FieldSpec,
    SystemMapIR,
)
from nlp2dsl_sdk.step_validation import validate_step_config_from_map


def _invoice_ir(*, attachment_required: bool = False) -> SystemMapIR:
    return SystemMapIR(
        example_id="01-invoice",
        data={
            "send_invoice.amount": 1500,
            "send_invoice.to": "klient@firma.pl",
            "send_invoice.currency": "PLN",
        },
        conversation=ConversationPolicyIR(
            autofill=True,
            attachment_required=attachment_required,
            generate_invoice_if_missing=True,
        ),
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                fields=[
                    FieldSpec(name="amount", required=True),
                    FieldSpec(name="to", required=True),
                    FieldSpec(name="attachment_path", required=False),
                ],
            )
        ],
    )


def test_build_target_plan_from_data() -> None:
    ir = _invoice_ir()
    target = build_target_plan(ir, "send_invoice", {})
    assert target.steps[0].config["amount"] == 1500
    assert target.steps[0].config["to"] == "klient@firma.pl"


def test_reflect_ready_when_complete() -> None:
    ir = _invoice_ir()
    ir.conversation.generate_invoice_if_missing = False
    target = build_target_plan(ir, "send_invoice", {"amount": 1500, "to": "a@b.pl"})
    report = reflect(
        "dsl_ready",
        target,
        {"amount": 1500, "to": "a@b.pl", "currency": "PLN"},
        ir=ir,
    )
    assert report.ready
    assert report.context_queries == []


def test_reflect_missing_attachment_when_required() -> None:
    ir = _invoice_ir(attachment_required=True)
    target = build_target_plan(ir, "send_invoice", {"amount": 1500, "to": "a@b.pl"})
    report = reflect(
        "preflight",
        target,
        {"amount": 1500, "to": "a@b.pl"},
        ir=ir,
    )
    assert not report.ready
    assert any(i.field == "attachment_path" for i in report.issues)
    assert report.context_queries


def test_validate_attachment_mismatch(tmp_path: Path) -> None:
    ir = _invoice_ir()
    bad = tmp_path / "x.pdf"
    write_invoice_pdf(bad, to="a@b.pl", amount=999, currency="PLN")
    issues = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": str(bad)},
    )
    assert any("kwota" in i for i in issues)
    report = reflect_from_chat_turn(
        ir,
        {"status": "ready", "dsl": {"steps": [{"action": "send_invoice", "config": {"amount": 1500, "to": "a@b.pl", "attachment_path": str(bad)}}]}},
        "validation_failed",
        validation_issues=issues,
    )
    assert not report.ready
    summary = format_reflection_summary(report)
    assert "Refleksja" in summary
