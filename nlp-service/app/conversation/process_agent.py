"""
ProcessAgent — preflight before DSL build / user questions.

Phases (same turn):
  1. Load DOQL system map
  2. Runtime availability gate
  3. DOQL autofill + nested generate_invoice
  4. (future) LLM clarification
"""

from __future__ import annotations

import logging

from app.conversation.doql_autofill import load_context_for_state, sync_autofill_from_doql
from app.conversation.doql_registry import refresh_registry_for_state, reload_context_after_refresh
from app.conversation.reflection import reflection_from_state
from app.conversation.runtime_gate import runtime_unavailable_message
from app.conversation.system_map import set_doql_context
from app.routing import IntentDecision
from app.schemas import ConversationResponse, ConversationState

log = logging.getLogger("orchestrator.process_agent")


async def preflight_turn(
    state: ConversationState,
    decision: IntentDecision,
) -> ConversationResponse | None:
    """
    Run environment preflight. Returns blocked response or None to continue pipeline.
    Sets DOQL context ContextVar for mapper / delegate.
    """
    ctx = load_context_for_state(state)
    set_doql_context(ctx)

    if ctx is not None and state.intent:
        blocked = runtime_unavailable_message(ctx, state.intent)
        if blocked:
            state.history.append({"role": "assistant", "text": blocked})
            log.info("Preflight blocked: %s", blocked[:80])
            return ConversationResponse(
                conversation_id=state.id,
                status="blocked",
                message=blocked,
            )

    applied = await sync_autofill_from_doql(state)
    if applied:
        log.info("Preflight autofill: %s", applied)

    refresh_registry_for_state(
        state,
        phase="preflight_autofill" if applied else "preflight",
    )
    reload_context_after_refresh(state)

    return None


def reflect_turn(state: ConversationState, phase: str) -> dict:
    """Reflection report after a process decision (target vs current)."""
    report = reflection_from_state(state, phase)
    if not report.get("ready"):
        log.info(
            "Reflection [%s]: %d issue(s), query=%s",
            phase,
            len(report.get("issues") or []),
            (report.get("context_queries") or [None])[0],
        )
    return report


async def observe_turn(
    state: ConversationState,
    *,
    phase: str,
    execution: dict | None = None,
) -> None:
    """Write current state / execution back to environment.doql.less."""
    path = refresh_registry_for_state(state, phase=phase, execution=execution)
    if path:
        reload_context_after_refresh(state)
