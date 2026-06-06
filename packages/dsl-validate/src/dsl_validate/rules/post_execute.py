"""Post-execute validation — worker outcome + attachment artifacts."""

from __future__ import annotations

from typing import Any

from ..context import ValidationContext
from ..issue import Phase, ValidationIssue
from .step_config import validate_step


def validate_execution_outcome(
    execution: dict[str, Any],
    *,
    dsl: dict[str, Any] | None = None,
    path_resolver=None,
    path_scope_check=None,
) -> list[ValidationIssue]:
    """Validate completed workflow execution (step status + optional attachment re-check)."""
    issues: list[ValidationIssue] = []
    steps = execution.get("steps") or []
    if not isinstance(steps, list):
        return [
            ValidationIssue(
                code="execution.invalid_payload",
                field_name="steps",
                message="execution.steps must be a list",
                phase=Phase.POST_EXECUTE,
                kind="invalid_format",
                resolution="blocked",
            )
        ]

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        status = str(step.get("status") or "")
        action = str(step.get("action") or "")
        if status == "failed":
            err = step.get("error") or step.get("detail") or "unknown error"
            issues.append(
                ValidationIssue(
                    code="execution.step_failed",
                    field_name="status",
                    message=f"krok {index + 1} ({action or '?'}): {err}",
                    phase=Phase.POST_EXECUTE,
                    kind="blocked",
                    resolution="blocked",
                    meta={"step_index": index, "action": action},
                )
            )

    if dsl and path_resolver is not None:
        for step in dsl.get("steps") or []:
            if not isinstance(step, dict):
                continue
            action = str(step.get("action") or "")
            config = dict(step.get("config") or {})
            raw = str(config.get("attachment_path") or "").strip()
            if not raw:
                continue
            ctx = ValidationContext(
                phase=Phase.POST_EXECUTE,
                action=action,
                config=config,
                path_resolver=path_resolver,
                path_scope_check=path_scope_check,
            )
            issues.extend(validate_step(ctx))

    return issues
