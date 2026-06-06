"""DOQL context — SDK shim + nlp-service conversation helpers (C2)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nlp2dsl_sdk.doql.models import (
    DoqlArtifact,
    DoqlCommand,
    DoqlProcessPolicy,
    DoqlRuntime,
    DoqlTaskContext,
)
from nlp2dsl_sdk.doql.parse import load_doql_context

__all__ = [
    "DoqlArtifact",
    "DoqlCommand",
    "DoqlProcessPolicy",
    "DoqlRuntime",
    "DoqlTaskContext",
    "autofill_entities",
    "load_doql_context",
    "merge_inline_context",
    "resolve_doql_context_path",
]


def resolve_doql_context_path(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
    raw = os.environ.get("NLP2DSL_DOQL_CONTEXT", "").strip()
    if raw:
        path = Path(raw)
        if path.is_file():
            return path
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        root = Path(example_dir)
        for candidate in (
            root / ".nlp2dsl" / "registry" / "environment.doql.less",
            root / ".nlp2dsl" / "environment.doql.less",
        ):
            if candidate.is_file():
                return candidate
    from nlp2dsl_sdk.doql.runtime import resolve_doql_context_path as sdk_resolve

    return sdk_resolve()


def merge_inline_context(ctx: DoqlTaskContext, inline: dict[str, Any]) -> DoqlTaskContext:
    if not inline:
        return ctx
    merged_data = dict(ctx.data)
    for key, value in inline.items():
        if value is None:
            continue
        camel = {
            "attachmentPath": "attachment_path",
            "attachment_path": "attachment_path",
            "amount": "send_invoice.amount",
            "to": "send_invoice.to",
            "currency": "send_invoice.currency",
            "attachment_required": "conversation.attachment_required",
            "generate_invoice_if_missing": "conversation.generate_invoice_if_missing",
            "strict_pdf": "conversation.strict_pdf",
        }
        mapped = camel.get(key, key)
        conv_key = key if key.startswith("conversation.") else mapped
        if conv_key.startswith("conversation."):
            flag = conv_key.split(".", 1)[1]
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
            continue
        if key in ("sync_auto_execute", "auto_execute"):
            ctx.sync_auto_execute = bool(value)
            continue
        if key in ("example_dir", "NLP2DSL_EXAMPLE_DIR"):
            continue
        merged_data[mapped] = value
        if key in ("amount", "to", "currency", "attachment_path", "attachmentPath"):
            short = mapped.split(".")[-1] if "." in mapped else mapped
            merged_data.setdefault(short, value)
        elif "." in key and key.count(".") == 1:
            _, short = key.split(".", 1)
            merged_data.setdefault(short, value)
    ctx.data = merged_data
    return ctx


def autofill_entities(
    entities: dict[str, Any],
    missing_refs: list[str],
    ctx: DoqlTaskContext,
    *,
    intent: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    if not ctx.autofill or not ctx.data:
        return entities, []

    updated = dict(entities)
    filled: list[str] = []
    alias_map = {"attachment": "attachment_path", "attachmentpath": "attachment_path"}

    for ref in list(missing_refs):
        if "." in ref:
            action, field = ref.split(".", 1)
        else:
            action = intent or "send_invoice"
            field = ref

        field = alias_map.get(field.lower(), field)
        if field == "attachment_path" and not ctx.attachment_required:
            continue
        candidates = [f"{action}.{field}", field, f"send_invoice.{field}"]
        value = None
        for key in candidates:
            if key in ctx.data and ctx.data[key] is not None:
                value = ctx.data[key]
                break
        if value is None:
            for art in ctx.artifacts:
                if field == "attachment_path" and art.path:
                    if not ctx.attachment_required:
                        break
                    value = art.path
                    break
                if field in art.values and art.values[field] is not None:
                    value = art.values[field]
                    break
        if value is not None and updated.get(field) is None:
            updated[field] = value
            filled.append(ref)

    return updated, filled
