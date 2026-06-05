"""Delegacja wykonania workflow do Mullm BFF vs worker lokalny."""

from __future__ import annotations

from typing import Any

from app.registry import DELEGATED_ACTIONS, MULLM_ACTIONS


def is_delegated_to_mullm(intent: str | None) -> bool:
    return bool(intent and intent in DELEGATED_ACTIONS)


def execution_backend_for_runtime(runtime_id: str | None) -> str:
    """Map DOQL runtime id → execution backend."""
    if not runtime_id:
        return "worker"
    if runtime_id == "delegate:mullm":
        return "mullm"
    if runtime_id == "orchestrator:nlp-service":
        return "system"
    return "worker"


def execution_backend_for_intent(intent: str | None) -> str:
    """Backend wykonania DSL: mullm | worker | system."""
    from app.conversation.system_map import get_doql_context, runtime_id_for_action

    if intent:
        ctx = get_doql_context()
        if ctx is not None:
            runtime_id = runtime_id_for_action(intent)
            if runtime_id:
                return execution_backend_for_runtime(runtime_id)
    return "mullm" if is_delegated_to_mullm(intent) else "worker"


def mullm_action_names() -> frozenset[str]:
    return frozenset(MULLM_ACTIONS)


def delegate_payload(action: str, config: dict[str, Any]) -> dict[str, Any]:
    """Kontrakt dla Mullm conductor._ready_action_payload."""
    return {
        "action": action,
        "config": config,
        "backend": "mullm",
    }
