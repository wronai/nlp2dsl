"""DOQL system map access for conversation turns (ContextVar + helpers)."""

from __future__ import annotations

from contextvars import ContextVar

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


def load_doql_from_path(path: str) -> DoqlTaskContext:
    return load_doql_context(path)
