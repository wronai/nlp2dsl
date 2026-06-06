"""Invoice attachment policy tests."""

from __future__ import annotations

from nlp2dsl_sdk.invoice_policy import apply_invoice_context, apply_invoice_policies, is_invoice_example
from nlp2dsl_sdk.doql_context import DoqlTaskContext, collect_task_context
from nlp2dsl_sdk.system_map_ir import SystemMapIR


def test_is_invoice_example() -> None:
    assert is_invoice_example("01-invoice")
    assert not is_invoice_example("02-email")


def test_apply_invoice_policies_on_ir() -> None:
    ir = SystemMapIR(example_id="01-invoice")
    apply_invoice_policies(ir)
    assert ir.conversation.attachment_required is True
    assert ir.conversation.generate_invoice_if_missing is True
    assert ir.conversation.strict_pdf is True
    assert "generate_invoice" in ir.capabilities


def test_collect_task_context_sets_invoice_policy(tmp_path) -> None:
    ex = tmp_path / "01-invoice"
    ex.mkdir()
    (ex / "fixtures").mkdir()
    ctx = collect_task_context(ex, example_name="01-invoice")
    assert ctx.attachment_required is True
    assert ctx.generate_invoice_if_missing is True
    assert ctx.strict_pdf is True


def test_apply_invoice_context() -> None:
    ctx = DoqlTaskContext(example_name="01-invoice", data={"attachment_path": ""})
    apply_invoice_context(ctx)
    assert ctx.attachment_required is True
    assert "attachment_path" not in ctx.data
