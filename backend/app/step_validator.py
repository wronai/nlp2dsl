"""Validate workflow step config before execution — SDK validation adapter."""

from __future__ import annotations

from typing import Any

from app.path_resolve import resolve_attachment_path
from nlp2dsl_sdk.validation.issue import Phase, ValidationIssue, issues_to_messages
from nlp2dsl_sdk.validation.context import ValidationContext
from nlp2dsl_sdk.validation.rules.step_config import validate_step

_REQUIRED: dict[str, list[str]] = {
    "send_invoice": ["amount", "to"],
    "generate_invoice": ["amount", "to"],
    "send_email": ["to", "subject", "body"],
    "generate_report": ["report_type"],
}

_QUALITY: dict[str, list[str]] = {
    "send_email": ["body"],
    "notify_slack": ["message"],
    "notify_telegram": ["message"],
    "notify_teams": ["message"],
}


def _validation_context(
    action: str,
    config: dict[str, Any],
    *,
    phase: Phase,
) -> ValidationContext:
    return ValidationContext(
        phase=phase,
        action=action,
        config=config,
        required_fields=list(_REQUIRED.get(action, [])),
        quality_fields=list(_QUALITY.get(action, [])),
        known_actions=None,
        path_resolver=resolve_attachment_path,
    )


def validate_step_config_issues(
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase = Phase.PRE_EXECUTE,
) -> list[ValidationIssue]:
    config = dict(config or {})
    return validate_step(_validation_context(action, config, phase=phase))


def validate_step_config(
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase = Phase.PRE_EXECUTE,
) -> list[str]:
    return issues_to_messages(validate_step_config_issues(action, config, phase=phase))
