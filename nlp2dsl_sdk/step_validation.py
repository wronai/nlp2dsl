"""Step validation using SystemMapIR — delegates to validation pipeline."""

from __future__ import annotations

from typing import Any

from .system_map_ir import SystemMapIR
from .validation import (
    Phase,
    ValidationIssue,
    validate_step_config_from_map as _validate_messages,
    validate_step_config_from_map_issues,
    validate_workflow_from_map as _validate_workflow,
    validate_workflow_from_map_issues,
)

__all__ = [
    "Phase",
    "ValidationIssue",
    "validate_step_config_from_map",
    "validate_step_config_from_map_issues",
    "validate_workflow_from_map",
    "validate_workflow_from_map_issues",
]


def validate_step_config_from_map(
    ir: SystemMapIR,
    action: str,
    config: dict[str, Any] | None,
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[str]:
    return _validate_messages(ir, action, config, phase=phase)


def validate_workflow_from_map(
    ir: SystemMapIR,
    steps: list[Any],
    *,
    phase: Phase = Phase.DSL_READY,
) -> list[tuple[int, str, list[str]]]:
    return _validate_workflow(ir, steps, phase=phase)
