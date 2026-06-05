"""Validate conversation TestTOON scenarios without testql.adapters.nlp2dsl."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_NLP_KINDS = frozenset({"nlp_dsl", "nlp2dsl"})
_ALLOWED_ENDPOINTS = frozenset({"chatstart", "chatmessage", "workflowfrom-text", "runworkflow"})
_ENDPOINT_RE = re.compile(
    r"^\s*(chatstart|chatmessage|workflowfrom-text|runworkflow)\s*,",
    re.MULTILINE | re.IGNORECASE,
)
_NLP_BLOCK_RE = re.compile(r"^NLP_DSL\s*\[", re.MULTILINE)


@dataclass
class ConversationValidation:
    passed: bool
    summary: str
    step_kinds: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def _is_nlp_kind(kind: str) -> bool:
    return kind.lower().replace("-", "_") in _NLP_KINDS


def _endpoints_from_text(text: str) -> list[str]:
    return [m.group(1).lower() for m in _ENDPOINT_RE.finditer(text)]


def validate_conversation_scenario(path: Path | str) -> ConversationValidation:
    """
    Parse and structurally validate a conversation TestTOON file.

    Uses testql.adapters.testtoon_adapter when available (no nlp2dsl adapter required).
    Falls back to scanning NLP_DSL rows when older testql builds omit step.extra metadata.
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
        kind = str(step.kind)
        if _is_nlp_kind(kind):
            endpoint = str(extra.get("endpoint", "")).strip().lower()
            if endpoint:
                endpoints.append(endpoint)
        elif kind in ("conversation", "conversation_turn"):
            if not extra.get("message") and not getattr(step, "name", None):
                issues.append("conversation step without message")

    if not endpoints:
        endpoints = _endpoints_from_text(text)

    has_nlp = any(_is_nlp_kind(k) for k in kinds) or bool(_NLP_BLOCK_RE.search(text))
    if not has_nlp:
        issues.append("no NLP_DSL steps")
    if not any(ep in _ALLOWED_ENDPOINTS for ep in endpoints):
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
