"""DSL structure contract validation before execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..issue import IssueKind, Phase, ValidationIssue


def validate_dsl_contract(
    dsl: Any,
    *,
    known_actions: set[str] | None = None,
    phase: Phase = Phase.DSL_READY,
) -> list[ValidationIssue]:
    """Validate the executable DSL envelope without enforcing action-specific config."""
    if not isinstance(dsl, Mapping):
        return [
            _issue(
                "dsl.invalid_type",
                "dsl",
                f"dsl: oczekiwano obiektu, otrzymano {_type_name(dsl)}",
                phase,
            )
        ]

    issues: list[ValidationIssue] = []
    _validate_optional_text_field(dsl, "name", issues, phase)
    _validate_optional_text_field(dsl, "trigger", issues, phase, allow_none=True)
    steps = dsl.get("steps")
    if not isinstance(steps, list):
        issues.append(
            _issue(
                "dsl.steps_invalid",
                "steps",
                f"steps: oczekiwano listy kroków, otrzymano {_type_name(steps)}",
                phase,
                kind="missing" if steps is None else "invalid_format",
            )
        )
        return issues

    if not steps:
        issues.append(
            _issue(
                "dsl.steps_empty",
                "steps",
                "steps: workflow musi zawierać przynajmniej jeden krok",
                phase,
                kind="missing",
            )
        )
        return issues

    for index, step in enumerate(steps):
        issues.extend(_validate_step(index, step, known_actions=known_actions, phase=phase))
    return issues


def _validate_step(
    index: int,
    step: Any,
    *,
    known_actions: set[str] | None,
    phase: Phase,
) -> list[ValidationIssue]:
    field = f"steps.{index}"
    if not isinstance(step, Mapping):
        return [
            _issue(
                "dsl.step.invalid_type",
                field,
                f"{field}: oczekiwano obiektu kroku, otrzymano {_type_name(step)}",
                phase,
            )
        ]

    issues: list[ValidationIssue] = []
    action = step.get("action")
    if not _is_non_empty_string(action):
        issues.append(
            ValidationIssue(
                code="workflow.missing_action",
                field_name=f"{field}.action",
                message="brak action w kroku workflow",
                phase=phase,
                kind="missing",
                resolution="blocked",
            )
        )
    elif known_actions is not None and str(action) not in known_actions:
        issues.append(
            ValidationIssue(
                code="action.unknown",
                field_name=f"{field}.action",
                message=f"unknown_action:{action}",
                phase=phase,
                kind="unknown_action",
                resolution="blocked",
                meta={"action": str(action), "index": index},
            )
        )

    if "config" in step and not isinstance(step.get("config"), Mapping):
        issues.append(
            _issue(
                "dsl.step.config_invalid",
                f"{field}.config",
                f"{field}.config: oczekiwano obiektu, otrzymano {_type_name(step.get('config'))}",
                phase,
            )
        )
    return issues


def _validate_optional_text_field(
    dsl: Mapping[str, Any],
    field: str,
    issues: list[ValidationIssue],
    phase: Phase,
    *,
    allow_none: bool = False,
) -> None:
    if field not in dsl:
        return
    value = dsl.get(field)
    if value is None and allow_none:
        return
    if not _is_non_empty_string(value):
        issues.append(
            _issue(
                f"dsl.{field}_invalid",
                field,
                f"{field}: oczekiwano niepustego tekstu, otrzymano {_type_name(value)}",
                phase,
            )
        )


def _issue(
    code: str,
    field: str,
    message: str,
    phase: Phase,
    *,
    kind: IssueKind = "invalid_format",
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        field_name=field,
        message=message,
        phase=phase,
        kind=kind,
        resolution="blocked",
    )


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    return type(value).__name__
