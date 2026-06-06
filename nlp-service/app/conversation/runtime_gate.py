"""Preflight: verify command runtime is available before autofill/execute."""

from __future__ import annotations

from app.conversation.doql_context import DoqlTaskContext
from nlp2dsl_sdk.validation.issue import Phase
from nlp2dsl_sdk.validation.pipeline import validate_post_health_for_intent


def runtime_unavailable_message(
    ctx: DoqlTaskContext,
    intent: str | None,
    *,
    live_probe: bool = True,
) -> str | None:
    """
    Return user-facing message when DOQL runtime is unavailable or health check fails.
    None when OK or map has no runtimes section (legacy DOQL).
    """
    if not intent or not ctx.runtimes:
        return None

    issues = validate_post_health_for_intent(
        ctx.runtimes,
        intent,
        live_probe=live_probe,
        phase=Phase.PREFLIGHT,
    )
    if issues:
        return issues[0].message

    from nlp2dsl_sdk.validation.rules.runtime_health import runtime_id_for_intent

    runtime_id = runtime_id_for_intent(intent)
    if not runtime_id:
        return None
    by_id = {r.id: r for r in ctx.runtimes}
    if runtime_id not in by_id:
        return None
    return None


def process_scope_blocked(
    ctx: DoqlTaskContext,
    *,
    action: str | None,
    resource_area: str | None,
) -> str | None:
    """Block when DOQL process_access denies the intent's resource area."""
    if not action:
        return None
    proc = ctx.process
    area = (resource_area or "").strip()
    deny = set(proc.deny_resource_areas or [])
    allow = set(proc.allow_resource_areas or [])

    if area and area in deny:
        return (
            f"Akcja `{action}` (obszar `{area}`) jest zablokowana polityką procesu "
            f"(process_access.deny_areas)."
        )
    if action.startswith("mullm_") and deny.intersection({"mullm:rag", "mullm", "mullm:*"}):
        return (
            f"Akcja `{action}` wymaga delegacji Mullm, a proces ma wycięty obszar Mullm "
            f"(process_access.deny_areas)."
        )
    if allow and area and area not in allow:
        return (
            f"Akcja `{action}` (obszar `{area}`) nie należy do dozwolonych obszarów procesu "
            f"({', '.join(sorted(allow))})."
        )
    return None


def intract_clarification_blocked(
    ctx: DoqlTaskContext,
    *,
    intent: str | None,
    confidence: float,
) -> str | None:
    """Block low-confidence / unknown intents when process.intract_enforce_clarification."""
    if not ctx.process.intract_enforce_clarification:
        return None
    threshold = float(ctx.process.nlp_confidence_min or 0.5)
    if intent == "unknown" or confidence < threshold:
        return (
            f"Intencja wymaga doprecyzowania (pewność {confidence:.2f}, próg {threshold:.2f}). "
            "Opisz dokładniej, co system ma zrobić."
        )
    return None
