"""Jedno miejsce: native → parser → authorize → IntentDecision."""

from __future__ import annotations

import os
from typing import Any

from app.governance.policy import AccessDecision, authorize_action, get_agent_id
from app.routing.native import resolve_native_intent
from app.routing.orientation import OrientationResult, orient_query
from app.routing.parser import parse_text
from app.routing.parser.rules import parse_rules
from app.conversation.system_map import (
    command_meta,
    effective_nlp_confidence_min,
    effective_nlp_parser_mode,
)
from app.registry import DELEGATED_ACTIONS
from app.routing.intent import IntentDecision
from app.routing.observability import record_intent_decision
from app.schemas import NLPResult

_FALLBACK_THRESHOLD = float(os.getenv("LLM_FALLBACK_THRESHOLD", "0.5"))


def _parser_source(text: str) -> str:
    """Etykieta źródła parsera (rules vs llm) — DOQL process policy lub NLP_CHAT_MODE."""
    mode = effective_nlp_parser_mode()
    if mode == "rules":
        return "rules"
    if mode == "llm":
        return "llm"
    threshold = effective_nlp_confidence_min()
    rules_result = parse_rules(text)
    if rules_result.intent.confidence >= threshold:
        return "rules"
    return "llm"


def _intent_from_native(native: dict[str, Any]) -> IntentDecision:
    action = str(native["action"])
    return IntentDecision(
        action=action,
        intent=action,
        confidence=0.95,
        source=str(native.get("source") or "native_routing"),
        reason_codes=["native_match"],
        resource_area=native.get("resource_area"),
        permission_action=str(native.get("permission_action") or "execute"),
        uri=native.get("uri"),
    )


def _intent_from_nlp(nlp: NLPResult, source: str) -> IntentDecision:
    action = nlp.intent.intent
    meta = command_meta(action)
    return IntentDecision(
        action=action,
        intent=action,
        confidence=float(nlp.intent.confidence),
        source=source,
        reason_codes=[f"parser_{source}"],
        resource_area=meta.get("resource_area"),
        permission_action=str(meta.get("permission_action") or "execute"),
        uri=meta.get("resource_uri"),
        candidate_actions=[
            {
                "action": action,
                "confidence": nlp.intent.confidence,
                "source": source,
            }
        ],
    )


def _apply_auth(decision: IntentDecision, auth: AccessDecision) -> IntentDecision:
    decision.agent_id = auth.agent_id
    decision.authorized = auth.allowed
    decision.deny_reason = None if auth.allowed else auth.reason
    decision.deny_effect = None if auth.allowed else auth.effect
    if not auth.allowed:
        decision.reason_codes.append(f"auth_{auth.effect}")
    else:
        decision.reason_codes.append("auth_allow")
    return decision


def _intent_from_orientation(
    text: str,
    orientation: OrientationResult,
    *,
    agent_id: str,
) -> IntentDecision | None:
    """Krótka ścieżka gdy orientacja ma wysoką pewność i znaną akcję."""
    if orientation.confidence < 0.8 or not orientation.suggested_action:
        return None
    action = orientation.suggested_action
    codes = list(orientation.reason_codes) + ["orientation_short_circuit"]
    decision = IntentDecision(
        action=action,
        intent=action,
        confidence=float(orientation.confidence),
        source="orientation",
        reason_codes=codes,
        agent_id=agent_id,
        orientation=orientation.to_dict(),
    )
    meta = command_meta(action)
    decision.resource_area = meta.get("resource_area")
    decision.permission_action = str(meta.get("permission_action") or "execute")
    decision.uri = meta.get("resource_uri")
    return decision


async def resolve_intent(
    text: str,
    *,
    agent_id: str | None = None,
    connector: str = "mullm",
) -> tuple[IntentDecision, NLPResult | None]:
    """
    Kaskada: orientacja → native_routing → parse_text → authorize.

    Zwraca (decyzja, NLPResult) — NLPResult jest None przy odmowie ACL lub gdy brak treści.
    """
    text = (text or "").strip()
    aid = get_agent_id(agent_id)
    orientation = orient_query(text, connector=connector)

    if not text:
        empty = IntentDecision(
            action=None,
            intent="empty",
            confidence=0.0,
            source="unknown",
            reason_codes=["empty_message"],
            agent_id=aid,
            authorized=False,
            deny_reason="empty_message",
        )
        record_intent_decision(empty)
        return empty, None

    oriented = _intent_from_orientation(text, orientation, agent_id=aid)
    if oriented and oriented.action in DELEGATED_ACTIONS:
        meta = command_meta(oriented.action or "")
        auth = authorize_action(aid, oriented.action or "", action_meta=meta)
        oriented = _apply_auth(oriented, auth)
        if oriented.authorized:
            record_intent_decision(oriented)
            nlp = oriented.to_nlp_result(text)
            if orientation.shell_command:
                nlp.entities = nlp.entities.model_copy(
                    update={"shell_command": orientation.shell_command}
                )
            return oriented, nlp
        record_intent_decision(oriented)
        return oriented, None

    native = resolve_native_intent(text)
    # Tylko trasy z nlp2dsl.yaml (native_routing) — aliasy z registry idą do parsera (entities)
    if native and native.get("source") == "native_routing":
        decision = _intent_from_native(native)
        decision.agent_id = aid
        meta = command_meta(decision.action or "")
        auth = authorize_action(
            aid,
            decision.action or "",
            resource_area=decision.resource_area,
            uri=decision.uri,
            permission_action=decision.permission_action,
            action_meta=meta,
        )
        decision = _apply_auth(decision, auth)
        if decision.authorized:
            record_intent_decision(decision)
            return decision, decision.to_nlp_result(text)
        record_intent_decision(decision)
        return decision, None

    nlp = await parse_text(text, mode=effective_nlp_parser_mode())
    source = _parser_source(text)
    decision = _intent_from_nlp(nlp, source)
    decision.agent_id = aid

    if decision.action in DELEGATED_ACTIONS:
        meta = command_meta(decision.action or "")
        auth = authorize_action(
            aid,
            decision.action or "",
            action_meta=meta,
        )
        decision = _apply_auth(decision, auth)
        if not decision.authorized:
            record_intent_decision(decision)
            return decision, None

    decision.reason_codes.append("auth_skipped")
    record_intent_decision(decision)
    return decision, nlp
