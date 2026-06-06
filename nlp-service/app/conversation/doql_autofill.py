"""Synchronously fill conversation entities from environment.doql.less."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from app.conversation.invoice_policy import invoice_attachment_policy_active
from app.conversation.attachment_gate import workflow_needs_attachment
from app.conversation.doql_context import (
    DoqlTaskContext,
    autofill_entities,
    load_doql_context,
    merge_inline_context,
    resolve_doql_context_path,
)
from app.conversation.responses import _nlp_from_state
from app.dsl.pipeline import map_to_dsl_with_enrichment
from app.schemas import ConversationState, DialogResponse

log = logging.getLogger("orchestrator.doql")

_MAX_AUTOFILL_ROUNDS = 5


def load_context_for_state(state: ConversationState) -> DoqlTaskContext | None:
    ctx: DoqlTaskContext | None = None
    path = resolve_doql_context_path(state.doql_context_path or None)
    if path:
        try:
            ctx = load_doql_context(path)
        except OSError as exc:
            log.warning("Failed to load DOQL context from %s: %s", path, exc)
    if ctx is None and state.doql_inline:
        ctx = DoqlTaskContext(data={}, autofill=True)
    if ctx is None:
        return None
    if state.doql_inline:
        ctx = merge_inline_context(ctx, state.doql_inline)
    return ctx


def _resolve_attachment_path(raw: str, ctx: DoqlTaskContext) -> str:
    from app.validation.path_resolve import resolve_attachment_path as resolve_path

    return resolve_path(raw, doql_path=resolve_doql_context_path())


def _nested_generate_invoice(state: ConversationState, ctx: DoqlTaskContext) -> str | None:
    """Synchronous nested step: materialize invoice file when attachment missing."""
    from app.conversation.invoice_paths import invoice_output_dir, store_attachment_path

    amount = state.entities.get("amount")
    to_addr = state.entities.get("to")
    if amount is None or not to_addr:
        return None

    doql = resolve_doql_context_path(state.doql_context_path or None)
    out_dir, ex_root = invoice_output_dir(doql_path=doql)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    currency = state.entities.get("currency", "PLN")
    amount_label = int(amount) if float(amount) == int(float(amount)) else amount
    filename = f"INV-{stamp}-{amount_label}-{currency}.pdf"
    out_path = out_dir / filename
    from app.validation.invoice_pdf import write_invoice_pdf

    write_invoice_pdf(out_path, to=str(to_addr), amount=amount, currency=str(currency))
    stored = store_attachment_path(out_path, ex_root)
    log.info("Nested generate_invoice → %s (stored as %s)", out_path, stored)
    ctx.data["send_invoice.attachment_path"] = stored
    return stored


async def sync_autofill_from_doql(state: ConversationState) -> list[str]:
    """
    Fill missing slots from DOQL data block (same turn, synchronous loop).
    Returns list of filled missing refs for audit trail.
    """
    ctx = load_context_for_state(state)
    if ctx is None or not ctx.autofill:
        return []

    if invoice_attachment_policy_active(ctx, state):
        state.attachment_required = True

    applied: list[str] = []
    for _ in range(_MAX_AUTOFILL_ROUNDS):
        dialog = await map_to_dsl_with_enrichment(_nlp_from_state(state))
        if dialog.status == "complete" and not workflow_needs_attachment(state, dialog, ctx):
            break
        if dialog.status == "complete" and workflow_needs_attachment(state, dialog, ctx):
            dialog = DialogResponse(
                status="incomplete",
                workflow=dialog.workflow,
                missing_fields=["send_invoice.attachment_path"],
                prompt_user="Podaj nazwę pliku faktury (PDF).",
            )

        missing = dialog.missing_fields or []
        if not missing:
            break

        updated, filled = autofill_entities(
            state.entities,
            missing,
            ctx,
            intent=state.intent,
        )
        if filled:
            state.entities.update(updated)
            applied.extend(filled)
            log.info("DOQL autofill applied: %s", filled)
            continue

        attachment_missing = any("attachment" in m for m in missing)
        need_attachment = attachment_missing or (
            invoice_attachment_policy_active(ctx, state)
            and not str(state.entities.get("attachment_path", "")).strip()
        )
        if (
            need_attachment
            and ctx.generate_invoice_if_missing
            and ("generate_invoice" in ctx.capabilities or not ctx.capabilities)
        ):
            generated = _nested_generate_invoice(state, ctx)
            if generated:
                state.entities["attachment_path"] = _resolve_attachment_path(generated, ctx)
                applied.append("send_invoice.attachment_path (nested generate_invoice)")
                continue
        break

    state.autofill_applied = list(dict.fromkeys(state.autofill_applied + applied))
    return applied
