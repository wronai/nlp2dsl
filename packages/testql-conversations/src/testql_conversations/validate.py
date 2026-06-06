"""Validate conversation TestTOON scenarios without testql.adapters.nlp2dsl."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


def _missing_type_header(text: str) -> str | None:
    if "TYPE: conversation" not in text:
        return "missing TYPE: conversation header"
    return None


def _parse_plan(path: Path) -> tuple[Any | None, str | None]:
    try:
        from testql.adapters.testtoon_adapter import TestToonAdapter
    except ImportError:
        return None, "testql not installed"

    try:
        return TestToonAdapter().parse(path), None
    except Exception as exc:
        return None, f"parse error: {exc}"


def _endpoints_from_steps(plan: Any, text: str) -> tuple[list[str], list[str]]:
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
    return endpoints, issues


def _structural_issues(kinds: list[str], endpoints: list[str], text: str) -> list[str]:
    issues: list[str] = []
    has_nlp = any(_is_nlp_kind(k) for k in kinds) or bool(_NLP_BLOCK_RE.search(text))
    if not has_nlp:
        issues.append("no NLP_DSL steps")
    if not any(ep in _ALLOWED_ENDPOINTS for ep in endpoints):
        issues.append("no chatstart/chatmessage/workflowfrom-text endpoints")
    return issues


def _validation_result(
    passed: bool,
    summary: str,
    *,
    kinds: list[str] | None = None,
    endpoints: list[str] | None = None,
    issues: list[str] | None = None,
) -> ConversationValidation:
    return ConversationValidation(
        passed,
        summary,
        step_kinds=kinds or [],
        endpoints=endpoints or [],
        issues=issues or [],
    )


def validate_conversation_scenario_text(text: str) -> ConversationValidation:
    """Structural checks from raw TestTOON text (no testql parse required)."""
    if header_issue := _missing_type_header(text):
        return _validation_result(False, header_issue)

    endpoints = _endpoints_from_text(text)
    issues = _structural_issues([], endpoints, text)
    if issues:
        return _validation_result(
            False,
            "; ".join(issues),
            endpoints=endpoints,
            issues=issues,
        )
    return _validation_result(
        True,
        f"text scan, endpoints={','.join(endpoints) or 'none'}",
        endpoints=endpoints,
    )


def validate_conversation_scenario(path: Path | str) -> ConversationValidation:
    """
    Parse and structurally validate a conversation TestTOON file.

    Uses testql.adapters.testtoon_adapter when available (no nlp2dsl adapter required).
    Falls back to scanning NLP_DSL rows when older testql builds omit step.extra metadata.
    """
    path = Path(path)
    if not path.is_file():
        return _validation_result(False, f"missing file: {path.name}")

    text = path.read_text(encoding="utf-8")
    if header_issue := _missing_type_header(text):
        return _validation_result(False, header_issue)

    plan, parse_error = _parse_plan(path)
    if parse_error == "testql not installed":
        return validate_conversation_scenario_text(text)
    if parse_error:
        return _validation_result(False, parse_error)
    if plan is None:
        return validate_conversation_scenario_text(text)

    kinds = [str(s.kind) for s in plan.steps]
    endpoints, step_issues = _endpoints_from_steps(plan, text)
    issues = step_issues + _structural_issues(kinds, endpoints, text)

    if issues:
        return _validation_result(
            False,
            "; ".join(issues),
            kinds=kinds,
            endpoints=endpoints,
            issues=issues,
        )

    return _validation_result(
        True,
        f"{len(plan.steps)} steps, endpoints={','.join(endpoints) or 'none'}",
        kinds=kinds,
        endpoints=endpoints,
    )


def dry_run_conversation_scenario(path: Path | str) -> ConversationValidation:
    """Alias for structural dry-run (no live HTTP)."""
    return validate_conversation_scenario(path)
