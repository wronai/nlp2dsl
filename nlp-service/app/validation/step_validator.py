"""Validate step config — adapter over nlp2dsl_sdk.validation pipeline."""

from __future__ import annotations

from typing import Any

from app.conversation.system_map import get_doql_context, known_action_names
from app.registry import get_quality_required_fields, get_required_fields
from app.validation.path_resolve import resolve_attachment_path
from nlp2dsl_sdk.validation.context import ValidationContext
from nlp2dsl_sdk.validation.issue import Phase, ValidationIssue, issues_to_messages
from nlp2dsl_sdk.validation.rules.step_config import validate_step


class StepValidationError(Exception):
    def __init__(self, action: str, issues: list[str]) -> None:
        self.action = action
        self.issues = issues
        super().__init__(f"{action}: {'; '.join(issues)}")


def _required_fields(action: str) -> list[str]:
    ctx = get_doql_context()
    if ctx is not None:
        doql_required = ctx.required_fields_for(action)
        if doql_required:
            return list(doql_required)
    return get_required_fields(action)


def _path_scope_check(resolved: str) -> str | None:
    ctx = get_doql_context()
    if ctx is None:
        return None
    from app.validation.path_policy import validate_process_path

    return validate_process_path(ctx, resolved, access="read")


def _path_resolver(raw: str) -> str:
    from app.conversation.doql_context import resolve_doql_context_path

    return resolve_attachment_path(raw, doql_path=resolve_doql_context_path())


def _validation_context(action: str, config: dict[str, Any]) -> ValidationContext:
    ctx = get_doql_context()
    attachment_required = bool(
        ctx is not None and ctx.attachment_required and action == "send_invoice"
    )
    return ValidationContext(
        phase=Phase.DSL_READY,
        action=action,
        config=dict(config),
        required_fields=_required_fields(action),
        quality_fields=list(get_quality_required_fields(action)),
        attachment_required=attachment_required,
        known_actions=known_action_names(),
        path_resolver=_path_resolver,
        path_scope_check=_path_scope_check,
    )


def validate_step_config_issues(action: str, config: dict[str, Any] | None) -> list[ValidationIssue]:
    """Return structured validation issues (empty list = OK)."""
    config = dict(config or {})
    if action not in known_action_names():
        return [
            ValidationIssue(
                code="action.unknown",
                field_name="action",
                message=f"unknown_action:{action}",
                phase=Phase.DSL_READY,
                kind="unknown_action",
                resolution="blocked",
                meta={"action": action},
            )
        ]
    vctx = _validation_context(action, config)
    return validate_step(vctx)


def validate_step_config(action: str, config: dict[str, Any] | None) -> list[str]:
    """Return validation issue messages (empty list = OK)."""
    return issues_to_messages(validate_step_config_issues(action, config))


def validate_workflow_steps(steps: list[Any]) -> list[tuple[int, str, list[str]]]:
    """Validate all steps; returns failures as (index, action, issues)."""
    failures: list[tuple[int, str, list[str]]] = []
    for index, step in enumerate(steps):
        action = getattr(step, "action", None) or (step.get("action") if isinstance(step, dict) else None)
        config = getattr(step, "config", None) or (step.get("config") if isinstance(step, dict) else {}) or {}
        if not action:
            failures.append((index, "?", ["brak action w kroku workflow"]))
            continue
        issues = validate_step_config(str(action), dict(config))
        if issues:
            failures.append((index, str(action), issues))
    return failures


def format_validation_message(failures: list[tuple[int, str, list[str]]]) -> str:
    lines = ["Walidacja kroku procesu nie powiodła się:"]
    for index, action, issues in failures:
        for issue in issues:
            lines.append(f"  • krok {index + 1} ({action}): {issue}")
    lines.append("Popraw dane lub załącznik przed wykonaniem.")
    return "\n".join(lines)
