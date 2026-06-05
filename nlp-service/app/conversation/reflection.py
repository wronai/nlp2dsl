"""Reflection bridge — align nlp-service state with SDK reflection model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.conversation.doql_autofill import load_context_for_state, resolve_doql_context_path
from app.schemas import ConversationState
from app.validation.step_validator import validate_step_config, validate_workflow_steps


def _intent_from_state(state: ConversationState) -> str:
    if state.intent:
        return state.intent
    if state.dsl and state.dsl.steps:
        return state.dsl.steps[0].action
    return "send_invoice"


def _current_config(state: ConversationState) -> dict[str, Any]:
    if state.dsl and state.dsl.steps:
        return dict(state.dsl.steps[0].config)
    return dict(state.entities)


def _target_config(state: ConversationState) -> dict[str, Any]:
    ctx = load_context_for_state(state)
    intent = _intent_from_state(state)
    config: dict[str, Any] = dict(state.entities)

    if ctx is not None:
        cmd = ctx.command(intent)
        if cmd:
            for field in cmd.required:
                if _empty(config.get(field)):
                    for key in (f"{intent}.{field}", field, f"send_invoice.{field}"):
                        if key in ctx.data and ctx.data[key] is not None:
                            config[field] = ctx.data[key]
                            break
        if ctx.attachment_required and intent == "send_invoice":
            config.setdefault("attachment_path", ctx.data.get("send_invoice.attachment_path", ""))
    return config


def _empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def _validation_issues(state: ConversationState) -> list[str]:
    if state.dsl:
        issues: list[str] = []
        for _idx, _action, step_issues in validate_workflow_steps(state.dsl.steps):
            issues.extend(step_issues)
        return issues
    return validate_step_config(_intent_from_state(state), _current_config(state))


def _policies(state: ConversationState) -> dict[str, Any]:
    ctx = load_context_for_state(state)
    if ctx is None:
        return {}
    return {
        "autofill": ctx.autofill,
        "attachment_required": ctx.attachment_required,
        "generate_invoice_if_missing": ctx.generate_invoice_if_missing,
    }


def _pseudo_response(state: ConversationState) -> dict[str, Any]:
    return {
        "status": state.status,
        "dsl": state.dsl.model_dump() if state.dsl else None,
        "missing": state.missing,
    }


def _resolve_doql_path(state: ConversationState) -> Path | None:
    raw = state.doql_context_path or ""
    if raw:
        path = Path(raw)
        if path.is_file():
            return path
    resolved = resolve_doql_context_path(state.doql_context_path)
    return resolved


def reflection_from_state(state: ConversationState, phase: str) -> dict[str, Any]:
    """Build reflection report dict (SDK schema when nlp2dsl_sdk is importable)."""
    validation_issues = _validation_issues(state)
    pseudo = _pseudo_response(state)

    path = _resolve_doql_path(state)
    if path is not None:
        try:
            from nlp2dsl_sdk.reflection import reflect_from_chat_turn
            from nlp2dsl_sdk.system_map_bridge import doql_file_to_system_map

            ir = doql_file_to_system_map(path)
            return reflect_from_chat_turn(
                ir,
                pseudo,
                phase,
                validation_issues=validation_issues,
            ).model_dump()
        except ImportError:
            pass

    intent = _intent_from_state(state)
    current = _current_config(state)
    target = _target_config(state)
    issues = [{"phase": phase, "kind": "mismatch", "field": "", "message": m, "resolution": "ask_user"} for m in validation_issues]

    queries: list[str] = []
    for raw in validation_issues:
        if "attachment_path" in raw:
            queries.append("Podaj plik faktury (PDF) lub włącz generate_invoice.")
        elif "to" in raw:
            queries.append("Podaj adres e-mail odbiorcy.")
        elif "amount" in raw:
            queries.append("Podaj kwotę faktury.")
        else:
            queries.append(raw)

    return {
        "phase": phase,
        "ready": len(issues) == 0,
        "target": {
            "intent": intent,
            "steps": [{"action": intent, "config": target}],
            "policies": _policies(state),
        },
        "current": current,
        "issues": issues,
        "context_queries": list(dict.fromkeys(queries)),
        "resolutions_available": [],
    }
