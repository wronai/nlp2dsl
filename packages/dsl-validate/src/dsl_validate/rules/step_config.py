"""Step config validation rules."""

from __future__ import annotations

from typing import Any

from ..context import ValidationContext
from ..helpers import is_empty, parse_amount
from ..issue import Phase, ValidationIssue
from .attachment import attachment_issues_for_config


def validate_step(ctx: ValidationContext) -> list[ValidationIssue]:
    if ctx.phase == Phase.POST_HEALTH:
        from .runtime_health import validate_runtime_health

        runtimes = getattr(ctx, "runtimes", None) or []
        runtime_id = getattr(ctx, "runtime_id", None)
        return validate_runtime_health(runtimes, runtime_id, phase=ctx.phase, live_probe=True)

    issues: list[ValidationIssue] = []
    config = ctx.config
    action = ctx.action

    if ctx.known_actions is not None and action not in ctx.known_actions:
        return [
            ValidationIssue(
                code="action.unknown",
                field_name="action",
                message=f"unknown_action:{action}",
                phase=ctx.phase,
                kind="unknown_action",
                resolution="blocked",
                meta={"action": action},
            )
        ]

    if ctx.phase not in (Phase.POST_EXECUTE, Phase.POST_HEALTH):
        for req in ctx.required_fields:
            if is_empty(config.get(req)):
                issues.append(
                    ValidationIssue(
                        code="field.missing",
                        field_name=req,
                        message=f"brak wymaganego pola: {req}",
                        phase=ctx.phase,
                        kind="missing",
                        resolution="ask_user",
                    )
                )

    if ctx.attachment_required and action == "send_invoice":
        if is_empty(config.get("attachment_path")):
            issues.append(
                ValidationIssue(
                    code="attachment.missing",
                    field_name="attachment_path",
                    message="brak attachment_path (conversation.attachment_required)",
                    phase=ctx.phase,
                    kind="missing",
                    resolution="generate",
                    source_hint="generate_invoice",
                )
            )

    for qf in ctx.quality_fields:
        if is_empty(config.get(qf)):
            issues.append(
                ValidationIssue(
                    code="field.quality_missing",
                    field_name=qf,
                    message=f"brak pola jakości: {qf}",
                    phase=ctx.phase,
                    kind="missing",
                    resolution="ask_user",
                )
            )

    issues.extend(_format_issues(ctx))
    return issues


def _format_issues(ctx: ValidationContext) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    config = ctx.config
    action = ctx.action

    amount = parse_amount(config.get("amount"))
    to_val = config.get("to")
    if not is_empty(to_val) and isinstance(to_val, str) and "@" not in to_val:
        issues.append(
            ValidationIssue(
                code="field.invalid_email",
                field_name="to",
                message=f"to: nie wygląda na adres email: {to_val}",
                phase=ctx.phase,
                kind="invalid_format",
                resolution="fix_format",
            )
        )

    if amount is None and "amount" in config and not is_empty(config.get("amount")):
        issues.append(
            ValidationIssue(
                code="field.invalid_amount",
                field_name="amount",
                message=f"amount: nie jest liczbą: {config.get('amount')!r}",
                phase=ctx.phase,
                kind="invalid_format",
                resolution="fix_format",
            )
        )

    body = config.get("body")
    if (
        action == "send_email"
        and not is_empty(body)
        and isinstance(body, str)
        and len(body.strip()) < 3
    ):
        issues.append(
            ValidationIssue(
                code="field.invalid_body",
                field_name="body",
                message="body: treść e-maila jest zbyt krótka",
                phase=ctx.phase,
                kind="invalid_format",
                resolution="fix_format",
            )
        )

    issues.extend(attachment_issues_for_config(ctx))
    return issues


def validate_workflow_steps(
    contexts: list[ValidationContext],
) -> list[tuple[int, str, list[ValidationIssue]]]:
    failures: list[tuple[int, str, list[ValidationIssue]]] = []
    for index, ctx in enumerate(contexts):
        if not ctx.action:
            failures.append(
                (
                    index,
                    "?",
                    [
                        ValidationIssue(
                            code="workflow.missing_action",
                            field_name="action",
                            message="brak action w kroku workflow",
                            phase=ctx.phase,
                            kind="missing",
                            resolution="blocked",
                        )
                    ],
                )
            )
            continue
        step_issues = validate_step(ctx)
        if step_issues:
            failures.append((index, ctx.action, step_issues))
    return failures
