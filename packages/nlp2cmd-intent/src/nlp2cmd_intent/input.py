"""Analyze NL query into IntentIR (structure only, no execution)."""

from __future__ import annotations

from typing import Any

from nlp2cmd_intent.clarification import ensure_intent_clear


def analyze_query(
    query: str,
    *,
    include_plan: bool = False,
    enforce_clarification: bool | None = None,
) -> dict[str, Any]:
    """Build query structure: IntentIR and optional ExecutionPlanIR."""
    from nlp2cmd_intent import IntentPipeline

    intent_pipeline = IntentPipeline()
    intent = intent_pipeline.run(query)
    ensure_intent_clear(intent, enforced=enforce_clarification)
    out: dict[str, Any] = {
        "query": query,
        "intent_ir": intent.model_dump(mode="json"),
    }
    if include_plan:
        try:
            from nlp2cmd_planner import PlanningPipeline

            plan = PlanningPipeline(intent_pipeline=intent_pipeline).run(query)
            out["execution_plan_ir"] = plan.model_dump(mode="json")
        except Exception as exc:
            out["execution_plan_ir"] = None
            out["plan_error"] = str(exc)
    return out
