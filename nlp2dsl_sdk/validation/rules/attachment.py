"""Attachment PDF validation rule."""

from __future__ import annotations

from pathlib import Path

from ..context import ValidationContext
from ..helpers import is_empty, parse_amount, pdf_amount_mismatch, pdf_structure_issues
from ..issue import ValidationIssue


def _resolve_path(ctx: ValidationContext, path_str: str) -> str:
    if ctx.path_resolver is not None:
        return ctx.path_resolver(path_str)
    from ...path_resolve import resolve_attachment_path

    return resolve_attachment_path(path_str)


def validate_attachment_path(
    ctx: ValidationContext,
    path_str: str,
    *,
    expected_amount: float | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    resolved = _resolve_path(ctx, path_str)

    if ctx.path_scope_check is not None:
        scope_msg = ctx.path_scope_check(resolved)
        if scope_msg:
            issues.append(
                ValidationIssue(
                    code="attachment.path_denied",
                    field_name="attachment_path",
                    message=scope_msg,
                    phase=ctx.phase,
                    kind="blocked",
                    resolution="blocked",
                    meta={"resolved": resolved},
                )
            )
            return issues

    path = Path(resolved)
    if not path.is_file():
        msg = f"attachment_path: plik nie istnieje: {path_str}"
        if resolved != path_str:
            msg += f" (resolved: {resolved})"
        issues.append(
            ValidationIssue(
                code="attachment.missing_file",
                field_name="attachment_path",
                message=msg,
                phase=ctx.phase,
                kind="missing",
                resolution="generate",
                source_hint="generate_invoice",
                meta={"resolved": resolved},
            )
        )
        return issues

    try:
        data = path.read_bytes()
    except OSError as exc:
        issues.append(
            ValidationIssue(
                code="attachment.read_error",
                field_name="attachment_path",
                message=f"attachment_path: nie można odczytać pliku: {exc}",
                phase=ctx.phase,
                kind="invalid_format",
                resolution="generate",
            )
        )
        return issues

    for raw in pdf_structure_issues(data):
        code = "attachment.invalid_eof" if "%%EOF" in raw else "attachment.invalid_pdf"
        issues.append(
            ValidationIssue(
                code=code,
                field_name="attachment_path",
                message=raw,
                phase=ctx.phase,
                kind="invalid_format",
                resolution="generate",
                source_hint="generate_invoice",
            )
        )

    if not issues and expected_amount is not None:
        mismatch = pdf_amount_mismatch(data, expected_amount)
        if mismatch:
            issues.append(
                ValidationIssue(
                    code="attachment.amount_mismatch",
                    field_name="attachment_path",
                    message=mismatch,
                    phase=ctx.phase,
                    kind="invalid_format",
                    resolution="fix_format",
                )
            )

    return issues


def attachment_issues_for_config(ctx: ValidationContext) -> list[ValidationIssue]:
    attachment = ctx.config.get("attachment_path")
    if is_empty(attachment) or not isinstance(attachment, str):
        return []
    amount = parse_amount(ctx.config.get("amount"))
    return validate_attachment_path(ctx, attachment, expected_amount=amount)
