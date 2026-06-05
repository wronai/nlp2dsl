"""
Refresh environment.doql.less in nlp-service (live registry).

Uses nlp2dsl_sdk.doql_registry when importable; otherwise patches data +
workflow_history blocks in place (preserves runtimes/commands).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from app.conversation.doql_context import DoqlTaskContext, load_doql_context, resolve_doql_context_path
from app.schemas import ConversationState

log = logging.getLogger("orchestrator.doql_registry")

_DATA_RE = re.compile(r"data\s*\{[^}]*\}", re.DOTALL)
_WFH_RE = re.compile(r"workflow_history\s*\{[^}]*\}", re.DOTALL)


def _format_value(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        safe = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{safe}"'
    return str(val)


def _render_block(name: str, data: dict[str, Any]) -> str:
    lines = [f"{name} {{"]
    for key in sorted(data):
        lines.append(f"  {key}: {_format_value(data[key])};")
    lines.append("}")
    return "\n".join(lines)


def _entities_to_data(intent: str | None, entities: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    action = intent or "send_invoice"
    for key, value in entities.items():
        if value is None or str(key).startswith("_"):
            continue
        out[f"{action}.{key}"] = value
        out.setdefault(key, value)
    return out


def _patch_doql_file(
    path: Path,
    *,
    data_patch: dict[str, Any] | None = None,
    history_patch: dict[str, Any] | None = None,
) -> None:
    text = path.read_text(encoding="utf-8")
    ctx = load_doql_context(path)

    if data_patch:
        merged = dict(ctx.data)
        merged.update(data_patch)
        block = _render_block("data", merged)
        if _DATA_RE.search(text):
            text = _DATA_RE.sub(block, text, count=1)
        else:
            insert_at = text.find("\n\n", text.find("}"))
            text = text[: insert_at + 2] + block + "\n\n" + text[insert_at + 2 :]

    if history_patch:
        merged = dict(ctx.workflow_history)
        merged.update(history_patch)
        block = _render_block("workflow_history", merged)
        if _WFH_RE.search(text):
            text = _WFH_RE.sub(block, text, count=1)
        else:
            text = text.rstrip() + "\n\n" + block + "\n"

    path.write_text(text, encoding="utf-8")


def _try_sdk_refresh(
    path: Path,
    *,
    intent: str | None,
    entities: Mapping[str, Any] | None,
    execution: Mapping[str, Any] | None,
    phase: str,
) -> bool:
    try:
        import sys

        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from nlp2dsl_sdk.doql_registry import refresh_doql_registry

        refresh_doql_registry(
            path,
            intent=intent,
            entities=entities or {},
            execution=execution,
            phase=phase,
        )
        return True
    except Exception:
        log.debug("SDK doql_registry refresh unavailable", exc_info=True)
        return False


def refresh_registry_for_state(
    state: ConversationState,
    *,
    phase: str,
    execution: Mapping[str, Any] | None = None,
    explicit_path: str | None = None,
) -> Path | None:
    """
    Persist conversation/execution observations to environment.doql.less.
    Returns path when written, else None.
    """
    path = resolve_doql_context_path(explicit_path or state.doql_context_path)
    if path is None:
        return None

    entities = dict(state.entities)
    if _try_sdk_refresh(
        path,
        intent=state.intent,
        entities=entities,
        execution=execution,
        phase=phase,
    ):
        log.info("DOQL registry refreshed (SDK): %s phase=%s", path, phase)
        return path

    data_patch = _entities_to_data(state.intent, entities)
    history_patch: dict[str, Any] = {
        "last_phase": phase,
        "last_observed_at": datetime.now(UTC).isoformat(),
    }
    if state.intent:
        history_patch["last_intent"] = state.intent
    if state.id:
        history_patch["conversation_id"] = state.id
    if execution:
        history_patch["last_status"] = str(
            execution.get("status", execution.get("state", ""))
        )
        for step in execution.get("results") or execution.get("steps") or []:
            if not isinstance(step, dict):
                continue
            output = step.get("output") or step.get("result") or {}
            if isinstance(output, dict) and output.get("invoice_id"):
                data_patch["send_invoice.last_invoice_id"] = output["invoice_id"]
                history_patch["last_invoice_id"] = str(output["invoice_id"])

    try:
        _patch_doql_file(path, data_patch=data_patch, history_patch=history_patch)
        log.info("DOQL registry refreshed (patch): %s phase=%s", path, phase)
        return path
    except OSError as exc:
        log.warning("Could not refresh DOQL registry at %s: %s", path, exc)
        return None


def reload_context_after_refresh(state: ConversationState) -> DoqlTaskContext | None:
    """Re-read registry file into memory after refresh."""
    from app.conversation.doql_autofill import load_context_for_state
    from app.conversation.system_map import set_doql_context

    ctx = load_context_for_state(state)
    set_doql_context(ctx)
    return ctx
