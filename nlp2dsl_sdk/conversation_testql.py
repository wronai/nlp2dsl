"""Validate conversation TestTOON scenarios without testql.adapters.nlp2dsl."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConversationValidation:
    passed: bool
    summary: str
    step_kinds: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def validate_conversation_scenario(path: Path | str) -> ConversationValidation:
    """
    Parse and structurally validate a conversation TestTOON file.

    Uses testql.adapters.testtoon_adapter when available (no nlp2dsl adapter required).
    """
    path = Path(path)
    if not path.is_file():
        return ConversationValidation(False, f"missing file: {path.name}")

    text = path.read_text(encoding="utf-8")
    if "TYPE: conversation" not in text:
        return ConversationValidation(False, "missing TYPE: conversation header")

    try:
        from testql.adapters.testtoon_adapter import TestToonAdapter
    except ImportError:
        return ConversationValidation(False, "testql not installed")

    try:
        plan = TestToonAdapter().parse(path)
    except Exception as exc:
        return ConversationValidation(False, f"parse error: {exc}")

    kinds = [str(s.kind) for s in plan.steps]
    endpoints: list[str] = []
    issues: list[str] = []

    for step in plan.steps:
        extra = getattr(step, "extra", None) or {}
        if step.kind == "nlp_dsl":
            endpoint = str(extra.get("endpoint", "")).strip()
            if endpoint:
                endpoints.append(endpoint)
            else:
                issues.append("nlp_dsl step without endpoint")
        elif step.kind == "conversation":
            if not extra.get("message") and not getattr(step, "name", None):
                issues.append("conversation step without message")

    if not any(k == "nlp_dsl" for k in kinds):
        issues.append("no NLP_DSL steps")
    allowed = {"chatstart", "chatmessage", "workflowfrom-text", "runworkflow"}
    if not any(ep in allowed for ep in endpoints):
        issues.append("no chatstart/chatmessage/workflowfrom-text endpoints")

    if issues:
        return ConversationValidation(
            False,
            "; ".join(issues),
            step_kinds=kinds,
            endpoints=endpoints,
            issues=issues,
        )

    return ConversationValidation(
        True,
        f"{len(plan.steps)} steps, endpoints={','.join(endpoints) or 'none'}",
        step_kinds=kinds,
        endpoints=endpoints,
    )


def dry_run_conversation_scenario(path: Path | str) -> ConversationValidation:
    """Alias for structural dry-run (no live HTTP)."""
    return validate_conversation_scenario(path)
