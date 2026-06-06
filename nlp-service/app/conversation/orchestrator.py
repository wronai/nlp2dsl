"""
Conversation Orchestrator — stanowy dialog AI → DSL.

Pipeline: resolve_intent → merge → unknown → system → DSL → incomplete.
"""

import logging
from uuid import uuid4

from app.conversation.autonomous_loop import autonomous_resolve_turn
from app.conversation.doql_autofill import load_context_for_state
from app.conversation.process_agent import observe_turn, preflight_turn, reflect_turn
from app.conversation.system_map import set_doql_context
from app.conversation.merge import merge_into_state
from app.conversation.responses import (
    build_and_check_dsl,
    build_incomplete_response,
    check_execute_keyword,
    deny_message,
    handle_system_action,
    handle_unknown_intent,
)
from app.request_context import set_example_dir
from app.routing import IntentDecision, resolve_intent
from app.schemas import ConversationResponse, ConversationState, NLPIntent, NLPResult
from app.store import ConversationStore
from app.store.factory import get_conversation_store

log = logging.getLogger("orchestrator")

_store: ConversationStore | None = None

_CONVERSATION_ID_LENGTH: int = int("12")


def _conversation_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = get_conversation_store()
    return _store


def _apply_request_context(inline: dict | None) -> None:
    if not inline:
        return
    for key in ("example_dir", "NLP2DSL_EXAMPLE_DIR"):
        raw = inline.get(key)
        if raw:
            set_example_dir(str(raw))
            return


async def start_conversation(
    text: str,
    *,
    doql_context_path: str | None = None,
    context_inline: dict | None = None,
) -> ConversationResponse:
    state = ConversationState(id=uuid4().hex[:_CONVERSATION_ID_LENGTH])
    _apply_request_context(context_inline)
    if doql_context_path:
        state.doql_context_path = doql_context_path
    if context_inline:
        state.doql_inline = dict(context_inline)
        _merge_inline_entities(state, context_inline)
        if context_inline.get("attachment_required"):
            state.attachment_required = bool(context_inline["attachment_required"])
    state.history.append({"role": "user", "text": text})
    result = await _process_message(state, text)
    await _conversation_store().save(state.id, state.model_dump())
    return result


async def continue_conversation(
    conversation_id: str,
    text: str,
    *,
    context_inline: dict | None = None,
) -> ConversationResponse:
    store = _conversation_store()
    raw = await store.get(conversation_id)
    if not raw:
        log.info("Conversation %s not found; creating new state lazily", conversation_id)
        state = ConversationState(id=conversation_id)
    else:
        state = ConversationState(**raw)

    _apply_request_context(context_inline)
    if context_inline:
        state.doql_inline = {**state.doql_inline, **context_inline}
        _merge_inline_entities(state, context_inline)
        if context_inline.get("attachment_required"):
            state.attachment_required = bool(context_inline["attachment_required"])

    state.history.append({"role": "user", "text": text})
    result = await _process_message(state, text)
    await store.save(state.id, state.model_dump())
    return result


async def get_conversation(conversation_id: str) -> ConversationState | None:
    raw = await _conversation_store().get(conversation_id)
    if raw:
        return ConversationState(**raw)
    return None


async def mark_conversation_executed(
    conversation_id: str,
    execution: dict,
) -> ConversationState | None:
    """Persist executed status after backend runs workflow (idempotent guard for 'uruchom')."""
    store = _conversation_store()
    raw = await store.get(conversation_id)
    if not raw:
        return None
    state = ConversationState(**raw)
    if state.status == "executed" and state.execution:
        return state
    state.status = "executed"
    state.execution = execution
    await store.save(state.id, state.model_dump())
    return state


def _attach_routing(
    resp: ConversationResponse,
    decision: IntentDecision,
) -> ConversationResponse:
    resp.routing = decision.to_dict()
    return resp


def _entity_field_from_inline_key(key: str) -> str | None:
    """Map llmContext / context_json keys to conversation entity fields."""
    if key.startswith("conversation."):
        return None
    key_map = {
        "attachmentPath": "attachment_path",
        "attachment_path": "attachment_path",
        "amount": "amount",
        "to": "to",
        "currency": "currency",
        "recipient": "to",
    }
    if key in key_map:
        return key_map[key]
    if "." in key and key.count(".") == 1:
        _, field = key.split(".", 1)
        return key_map.get(field, field)
    return key_map.get(key, key)


def _merge_inline_entities(state: ConversationState, inline: dict) -> None:
    """Apply TestQL llmContext / inline context keys directly to entities."""
    for key, value in inline.items():
        if value is None or key in ("example_dir", "NLP2DSL_EXAMPLE_DIR"):
            continue
        field = _entity_field_from_inline_key(key)
        if field == "attachment_path" and not state.attachment_required:
            if not inline.get("conversation.attachment_required"):
                continue
        if field is not None:
            state.entities[field] = value


def _attach_autofill(resp: ConversationResponse, state: ConversationState) -> ConversationResponse:
    if state.autofill_applied:
        resp.autofill_applied = list(state.autofill_applied)
    if state.autonomous_steps:
        resp.autonomous_steps = list(state.autonomous_steps)
    return resp


def _attach_reflection(resp: ConversationResponse, state: ConversationState, phase: str) -> ConversationResponse:
    try:
        resp.reflection = reflect_turn(state, phase)
    except Exception:
        log.exception("Reflection failed for phase %s", phase)
    return resp


def _slot_fill_decision(state: ConversationState) -> IntentDecision:
    intent = state.intent or "unknown"
    return IntentDecision(
        action=intent,
        intent=intent,
        confidence=1.0,
        source="slot_fill",
        reason_codes=["conversation_slot_fill"],
    )


def _has_extracted_entities(result: NLPResult) -> bool:
    return bool(result.entities.model_dump(exclude_none=True))


async def _try_slot_fill_followup(
    state: ConversationState,
    text: str,
) -> ConversationResponse | None:
    """Fill known missing slots with rules-only parsing before falling back to LLM routing."""
    if not (state.intent and state.intent != "unknown" and state.status == "in_progress" and state.missing):
        return None

    from app.routing.parser.rules import parse_rules

    nlp = parse_rules(text)
    if not _has_extracted_entities(nlp):
        return None

    nlp = nlp.model_copy(
        update={"intent": NLPIntent(intent=state.intent, confidence=1.0)}
    )
    merge_into_state(state, nlp)
    decision = _slot_fill_decision(state)

    auto = await autonomous_resolve_turn(state)
    if auto.response:
        await observe_turn(state, phase="dsl_ready")
        phase = "dsl_ready" if auto.response.status == "ready" else "validation_failed"
        return _attach_reflection(
            _attach_autofill(_attach_routing(auto.response, decision), state),
            state,
            phase,
        )

    dsl_response = await build_and_check_dsl(state)
    if dsl_response:
        await observe_turn(state, phase="dsl_ready")
        phase = "dsl_ready" if dsl_response.status == "ready" else "validation_failed"
        return _attach_reflection(
            _attach_autofill(_attach_routing(dsl_response, decision), state),
            state,
            phase,
        )

    incomplete = await build_incomplete_response(state)
    await observe_turn(state, phase="incomplete")
    return _attach_reflection(
        _attach_autofill(_attach_routing(incomplete, decision), state),
        state,
        "incomplete",
    )


async def _process_message(state: ConversationState, text: str) -> ConversationResponse:
    execute_response = await check_execute_keyword(state, text)
    if execute_response:
        return execute_response

    ctx = load_context_for_state(state)
    set_doql_context(ctx)

    slot_response = await _try_slot_fill_followup(state, text)
    if slot_response:
        return slot_response

    decision, nlp = await resolve_intent(text)
    log.info(
        "Intent: action=%s source=%s conf=%.2f authorized=%s",
        decision.action,
        decision.source,
        decision.confidence,
        decision.authorized,
    )

    if nlp is None:
        msg = deny_message(decision)
        state.history.append({"role": "assistant", "text": msg})
        return _attach_routing(
            ConversationResponse(
                conversation_id=state.id,
                status="in_progress",
                message=msg,
            ),
            decision,
        )

    merge_into_state(state, nlp)

    blocked = await preflight_turn(state, decision)
    if blocked:
        return _attach_reflection(_attach_routing(blocked, decision), state, "preflight_blocked")

    auto = await autonomous_resolve_turn(state)
    if auto.response:
        await observe_turn(state, phase="dsl_ready")
        phase = "dsl_ready" if auto.response.status == "ready" else "validation_failed"
        ctx = load_context_for_state(state)
        if ctx and ctx.sync_auto_execute and auto.response.status == "ready":
            auto.response.auto_execute = True
            if "sync_auto_execute" not in (auto.response.message or ""):
                auto.response.message = (auto.response.message or "") + "\n(sync_auto_execute — backend wykona workflow)"
        return _attach_reflection(
            _attach_autofill(_attach_routing(auto.response, decision), state),
            state,
            phase,
        )

    unknown_response = handle_unknown_intent(state)
    if unknown_response:
        return _attach_reflection(
            _attach_autofill(_attach_routing(unknown_response, decision), state),
            state,
            "unknown_intent",
        )

    system_response = handle_system_action(state)
    if system_response:
        return _attach_reflection(
            _attach_autofill(_attach_routing(system_response, decision), state),
            state,
            "system_action",
        )

    dsl_response = await build_and_check_dsl(state)
    if dsl_response:
        await observe_turn(state, phase="dsl_ready")
        phase = "dsl_ready" if dsl_response.status == "ready" else "validation_failed"
        return _attach_reflection(
            _attach_autofill(_attach_routing(dsl_response, decision), state),
            state,
            phase,
        )

    incomplete = await build_incomplete_response(state)
    await observe_turn(state, phase="incomplete")
    return _attach_reflection(
        _attach_autofill(_attach_routing(incomplete, decision), state),
        state,
        "incomplete",
    )
