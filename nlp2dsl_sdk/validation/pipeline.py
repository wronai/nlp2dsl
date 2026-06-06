"""Validation pipeline — single entry for step/workflow validation."""

from __future__ import annotations

from typing import Any

from ..system_map_ir import SystemMapIR
from .context import ValidationContext
from .issue import Phase, ValidationIssue, issues_to_messages
from .rules.dsl_contract import validate_dsl_contract
from .rules.step_config import validate_step, validate_workflow_steps


def validate_step_issues(ctx: ValidationContext) -> list[ValidationIssue]:
    return validate_step(ctx)


def validate_step_messages(ctx: ValidationContext) -> list[str]:
    return issues_to_messages(validate_step(ctx))


def validate_dsl_contract_issues(
    dsl: Any,
    *,
    known_actions: set[str] | None = None,
    phase: Phase = Phase.DSL_READY,
) -> list[ValidationIssue]:
    return validate_dsl_contract(dsl, known_actions=known_actions, phase=phase)


def validate_dsl_contract_messages(
    dsl: Any,
    *,
    known_actions: set[str] | None = None,
    phase: Phase = Phase.DSL_READY,
) -> list[str]:
    return issues_to_messages(
        validate_dsl_contract(dsl, known_actions=known_actions, phase=phase)
    )


def validate_step_config_from_map(
    ir: SystemMapIR,
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[str]:
    """Legacy API — returns Polish issue strings."""
    ctx = _context_from_map(ir, action, config, phase=phase)
    if ctx is None:
        return [f"unknown_action:{action}"]
    return validate_step_messages(ctx)


def validate_step_config_from_map_issues(
    ir: SystemMapIR,
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[ValidationIssue]:
    ctx = _context_from_map(ir, action, config, phase=phase)
    if ctx is None:
        return [
            ValidationIssue(
                code="action.unknown",
                field_name="action",
                message=f"unknown_action:{action}",
                phase=phase,
                kind="unknown_action",
                resolution="blocked",
                meta={"action": action},
            )
        ]
    return validate_step(ctx)


def validate_workflow_from_map(
    ir: SystemMapIR,
    steps: list[Any],
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[tuple[int, str, list[str]]]:
    failures = validate_workflow_from_map_issues(ir, steps, phase=phase)
    return [(i, a, issues_to_messages(iss)) for i, a, iss in failures]


def validate_workflow_from_map_issues(
    ir: SystemMapIR,
    steps: list[Any],
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[tuple[int, str, list[ValidationIssue]]]:
    contexts: list[ValidationContext] = []
    for step in steps:
        action = getattr(step, "action", None) or (step.get("action") if isinstance(step, dict) else None)
        config = getattr(step, "config", None) or (step.get("config") if isinstance(step, dict) else {}) or {}
        if not action:
            contexts.append(ValidationContext(phase=phase, action="", config={}))
            continue
        ctx = _context_from_map(ir, str(action), dict(config), phase=phase)
        if ctx is None:
            ctx = ValidationContext(phase=phase, action=str(action), config=dict(config), known_actions=set())
        contexts.append(ctx)
    return validate_workflow_steps(contexts)


def _context_from_map(
    ir: SystemMapIR,
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase,
) -> ValidationContext | None:
    cmd = ir.command(action)
    if cmd is None:
        return None
    return ValidationContext(
        phase=phase,
        action=action,
        config=dict(config or {}),
        required_fields=list(cmd.required_names),
        attachment_required=bool(ir.conversation.attachment_required),
        known_actions={action},
    )
