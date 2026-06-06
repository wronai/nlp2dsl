"""DOQL system map access for conversation turns (ContextVar + helpers)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from app.conversation.doql_context import DoqlTaskContext, load_doql_context, resolve_doql_context_path
from app.schemas import ConversationState

_current_doql: ContextVar[DoqlTaskContext | None] = ContextVar("doql_context", default=None)


def set_doql_context(ctx: DoqlTaskContext | None) -> None:
    _current_doql.set(ctx)


def get_doql_context() -> DoqlTaskContext | None:
    return _current_doql.get()


def load_system_map_for_state(state: ConversationState) -> DoqlTaskContext | None:
    from app.conversation.doql_autofill import load_context_for_state

    return load_context_for_state(state)


def known_action_names() -> set[str]:
    """Action names from DOQL commands[] when map is active; else ACTIONS_REGISTRY (C1)."""
    from app.registry import ACTIONS_REGISTRY

    ctx = get_doql_context()
    if ctx and ctx.commands:
        return {cmd.name for cmd in ctx.commands if cmd.name}
    return set(ACTIONS_REGISTRY.keys())


def command_meta(action: str) -> dict[str, Any]:
    """Lightweight action metadata — DOQL command first, registry fallback."""
    from app.registry import ACTIONS_REGISTRY

    ctx = get_doql_context()
    if ctx:
        cmd = ctx.command(action)
        if cmd is not None:
            return {
                "required": list(cmd.required),
                "optional": list(cmd.optional),
                "runtime": cmd.runtime,
                "resource_area": ACTIONS_REGISTRY.get(action, {}).get("resource_area"),
            }
    return dict(ACTIONS_REGISTRY.get(action, {}))


def required_fields_for_action(action: str) -> list[str] | None:
    """Required fields from DOQL commands[] when map is active."""
    ctx = get_doql_context()
    if ctx is None:
        return None
    return ctx.required_fields_for(action)


def runtime_id_for_action(action: str) -> str | None:
    ctx = get_doql_context()
    if ctx is None:
        return None
    return ctx.runtime_for(action)


def effective_nlp_parser_mode() -> str:
    """NLP parser mode from DOQL process policy (rules | llm | auto)."""
    ctx = get_doql_context()
    if ctx is None:
        import os

        return (os.getenv("NLP_CHAT_MODE", "auto") or "auto").lower().strip()
    parser = (ctx.process.nlp_parser or "auto").lower()
    if parser in ("rules", "rules_first"):
        return "rules"
    if parser == "llm":
        return "llm"
    return "auto"


def effective_nlp_confidence_min() -> float:
    ctx = get_doql_context()
    if ctx is None:
        import os

        return float(os.getenv("LLM_FALLBACK_THRESHOLD", "0.5"))
    return float(ctx.process.nlp_confidence_min)


def autonomous_max_rounds() -> int:
    ctx = get_doql_context()
    if ctx is None:
        return 8
    return int(ctx.process.autonomous_max_rounds)


def autonomous_enabled() -> bool:
    ctx = get_doql_context()
    if ctx is None:
        return True
    return bool(ctx.autofill and ctx.process.autonomous_enabled)


def load_doql_from_path(path: str) -> DoqlTaskContext:
    return load_doql_context(path)
