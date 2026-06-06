"""DOQL runtime helpers — chat inline payload, autofill, path resolution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .models import DoqlTaskContext
from .parse import load_doql_context


def resolve_doql_context_path() -> Path | None:
    from ..artifact_layout import resolve_registry_path

    return resolve_registry_path()


def context_inline_payload(ctx: DoqlTaskContext) -> dict[str, Any]:
    """Serialize DOQL data for chat context_json (portable across client/server)."""
    inline = dict(ctx.data)
    for key, value in list(ctx.data.items()):
        if "." in key:
            _, field = key.split(".", 1)
            if field == "attachment_path" and not ctx.attachment_required:
                inline.pop(key, None)
                continue
            inline.setdefault(field, value)
    for art in ctx.artifacts:
        for key, value in art.values.items():
            inline.setdefault(f"send_invoice.{key}", value)
            inline.setdefault(key, value)
    if not ctx.attachment_required:
        inline.pop("attachment_path", None)
        inline.pop("send_invoice.attachment_path", None)
    inline["conversation.autofill"] = ctx.autofill
    if ctx.attachment_required:
        inline["conversation.attachment_required"] = ctx.attachment_required
    if ctx.generate_invoice_if_missing:
        inline["conversation.generate_invoice_if_missing"] = ctx.generate_invoice_if_missing
    if ctx.strict_pdf:
        inline["conversation.strict_pdf"] = ctx.strict_pdf
    if ctx.sync_auto_execute:
        inline["conversation.sync_auto_execute"] = ctx.sync_auto_execute
        inline["sync_auto_execute"] = ctx.sync_auto_execute
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        mount = os.environ.get("NLP2DSL_EXAMPLES_MOUNT", "").strip()
        if mount:
            inline["example_dir"] = str(Path(mount) / Path(example_dir).name)
        else:
            inline["example_dir"] = example_dir
    return inline


def load_doql_inline_from_env() -> dict[str, Any]:
    path = resolve_doql_context_path()
    if not path:
        return {}
    return context_inline_payload(load_doql_context(path))


def merge_inline_context(ctx: DoqlTaskContext, inline: dict[str, Any]) -> DoqlTaskContext:
    """Merge portable chat context_json values into a DOQL task context."""
    if not inline:
        return ctx

    merged_data = dict(ctx.data)
    for key, value in inline.items():
        if value is None:
            continue

        mapped = _inline_data_key(key)
        conv_key = key if key.startswith("conversation.") else mapped
        if conv_key.startswith("conversation."):
            _apply_conversation_flag(ctx, conv_key.split(".", 1)[1], value)
            continue
        if key in ("sync_auto_execute", "auto_execute"):
            ctx.sync_auto_execute = bool(value)
            continue
        if key in ("example_dir", "NLP2DSL_EXAMPLE_DIR"):
            continue

        merged_data[mapped] = value
        _add_short_inline_alias(merged_data, key, mapped, value)

    ctx.data = merged_data
    return ctx


def autofill_entities(
    entities: dict[str, Any],
    missing_refs: list[str],
    ctx: DoqlTaskContext,
    *,
    intent: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Fill missing action.field slots from ctx.data. Returns (updated_entities, filled_keys)."""
    if not ctx.autofill or not ctx.data:
        return entities, []

    updated = dict(entities)
    filled: list[str] = []

    for ref in list(missing_refs):
        action, field = _split_missing_ref(ref, updated, intent=intent)
        if field == "attachment_path" and not ctx.attachment_required:
            continue
        value = _autofill_value(action, field, ctx)
        if value is not None and _needs_field(updated, field):
            updated[field] = value
            filled.append(ref)

    return updated, filled


def _inline_data_key(key: str) -> str:
    return {
        "attachmentPath": "attachment_path",
        "attachment_path": "attachment_path",
        "amount": "send_invoice.amount",
        "to": "send_invoice.to",
        "currency": "send_invoice.currency",
        "attachment_required": "conversation.attachment_required",
        "generate_invoice_if_missing": "conversation.generate_invoice_if_missing",
        "strict_pdf": "conversation.strict_pdf",
    }.get(key, key)


def _apply_conversation_flag(ctx: DoqlTaskContext, flag: str, value: Any) -> None:
    if flag == "attachment_required":
        ctx.attachment_required = bool(value)
    elif flag == "generate_invoice_if_missing":
        ctx.generate_invoice_if_missing = bool(value)
    elif flag == "strict_pdf":
        ctx.strict_pdf = bool(value)
    elif flag == "autofill":
        ctx.autofill = bool(value)
    elif flag == "sync_auto_execute":
        ctx.sync_auto_execute = bool(value)


def _add_short_inline_alias(
    merged_data: dict[str, Any],
    key: str,
    mapped: str,
    value: Any,
) -> None:
    if key in ("amount", "to", "currency", "attachment_path", "attachmentPath"):
        short = mapped.split(".")[-1] if "." in mapped else mapped
        merged_data.setdefault(short, value)
    elif "." in key and key.count(".") == 1:
        _, short = key.split(".", 1)
        merged_data.setdefault(short, value)


def _split_missing_ref(
    ref: str,
    entities: dict[str, Any],
    *,
    intent: str | None = None,
) -> tuple[str, str]:
    if "." in ref:
        action, field = ref.split(".", 1)
    else:
        action, field = (intent or entities.get("intent") or "send_invoice"), ref
    return str(action), _canonical_field(field)


def _canonical_field(field: str) -> str:
    alias_map = {
        "attachment": "attachment_path",
        "attachmentpath": "attachment_path",
    }
    return alias_map.get(field.lower(), field)


def _autofill_value(action: str, field: str, ctx: DoqlTaskContext) -> Any:
    value = _value_from_data(_candidate_data_keys(action, field), ctx)
    if value is not None:
        return value
    return _value_from_artifacts(field, ctx)


def _candidate_data_keys(action: str, field: str) -> list[str]:
    return [f"{action}.{field}", field, f"send_invoice.{field}"]


def _value_from_data(candidates: list[str], ctx: DoqlTaskContext) -> Any:
    for key in candidates:
        if key in ctx.data and ctx.data[key] is not None:
            return ctx.data[key]
    return None


def _value_from_artifacts(field: str, ctx: DoqlTaskContext) -> Any:
    for art in ctx.artifacts:
        if field == "attachment_path" and art.path:
            return art.path
        if field in art.values and art.values[field] is not None:
            return art.values[field]
    return None


def _needs_field(entities: dict[str, Any], field: str) -> bool:
    return entities.get(field) is None
