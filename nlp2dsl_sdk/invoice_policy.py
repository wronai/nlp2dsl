"""Invoice attachment policy — generate or ask; never skip with attachment_required: false."""

from __future__ import annotations

from typing import Any

from .system_map_ir import SystemMapIR


def is_invoice_example(example_id: str) -> bool:
    return "invoice" in (example_id or "").lower()


def apply_invoice_policies(
    ir: SystemMapIR,
    *,
    example_id: str | None = None,
    attachment: bool | None = None,
) -> None:
    """
    For invoice examples: require attachment resolution (fixture → generate_invoice → ask user).

    Pass attachment=False to opt out explicitly (non-invoice-style demos only).
    """
    ex_id = example_id or ir.example_id
    if attachment is False:
        return
    if attachment is not True and not is_invoice_example(ex_id):
        return

    ir.conversation.attachment_required = True
    ir.conversation.generate_invoice_if_missing = True
    ir.conversation.strict_pdf = True
    ir.data.pop("send_invoice.attachment_path", None)
    ir.data.pop("attachment_path", None)
    caps = set(ir.capabilities)
    caps.add("generate_invoice")
    ir.capabilities = sorted(caps)


def apply_invoice_context(ctx: Any) -> None:
    """Apply invoice attachment policy to bootstrap DoqlTaskContext."""
    if not is_invoice_example(getattr(ctx, "example_name", "")):
        return
    ctx.attachment_required = True
    ctx.generate_invoice_if_missing = True
    ctx.strict_pdf = True
    ctx.data.pop("send_invoice.attachment_path", None)
    ctx.data.pop("attachment_path", None)
    caps = set(getattr(ctx, "capabilities", []) or [])
    caps.add("generate_invoice")
    ctx.capabilities = sorted(caps)
