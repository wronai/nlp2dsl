"""Map legacy Polish validation strings ↔ ValidationIssue."""

from __future__ import annotations

from collections.abc import Callable

from .issue import IssueKind, Resolution, ValidationIssue

IssueParser = Callable[[str], ValidationIssue | None]


def legacy_message_to_issue(raw: str, *, phase_str: str = "validate") -> ValidationIssue:
    """Parse orchestrator/step_validator message into structured issue."""
    _ = phase_str
    for parser in _MESSAGE_PARSERS:
        issue = parser(raw)
        if issue is not None:
            return issue
    return _other_issue(raw)


def _missing_required_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("brak wymaganego pola:"):
        return ValidationIssue(
            code="field.missing",
            field_name=_field_after_colon(raw),
            message=raw,
            kind="missing",
            resolution="ask_user",
        )
    return None


def _quality_missing_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("brak pola jakości:"):
        return ValidationIssue(
            code="field.quality_missing",
            field_name=_field_after_colon(raw),
            message=raw,
            kind="missing",
            resolution="ask_user",
        )
    return None


def _attachment_missing_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("brak attachment_path"):
        return ValidationIssue(
            code="attachment.missing",
            field_name="attachment_path",
            message=raw,
            kind="missing",
            resolution="generate",
            source_hint="generate_invoice",
        )
    return None


def _attachment_issue(raw: str) -> ValidationIssue | None:
    if "attachment_path" in raw:
        resolution = _attachment_resolution(raw)
        return ValidationIssue(
            code=_attachment_code(raw),
            field_name="attachment_path",
            message=raw,
            kind=_attachment_kind(raw),
            resolution=resolution,
            source_hint="generate_invoice" if resolution == "generate" else None,
        )
    return None


def _field_format_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("to:"):
        return _invalid_field_issue(raw, code="field.invalid_email", field="to")
    if raw.startswith("amount:"):
        return _invalid_field_issue(raw, code="field.invalid_amount", field="amount")
    if raw.startswith("body:"):
        return _invalid_field_issue(raw, code="field.invalid_body", field="body")
    return None


def _unknown_action_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("unknown_action:"):
        action = _field_after_colon(raw)
        return ValidationIssue(
            code="action.unknown",
            field_name="action",
            message=raw,
            kind="unknown_action",
            resolution="blocked",
            meta={"action": action},
        )
    return None


def _missing_action_issue(raw: str) -> ValidationIssue | None:
    if raw.startswith("brak action"):
        return ValidationIssue(
            code="workflow.missing_action",
            field_name="action",
            message=raw,
            kind="missing",
            resolution="blocked",
        )
    return None


_MESSAGE_PARSERS: tuple[IssueParser, ...] = (
    _missing_required_issue,
    _quality_missing_issue,
    _attachment_missing_issue,
    _attachment_issue,
    _field_format_issue,
    _unknown_action_issue,
    _missing_action_issue,
)


def _field_after_colon(raw: str) -> str:
    return raw.split(":", 1)[1].strip()


def _invalid_field_issue(raw: str, *, code: str, field: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        field_name=field,
        message=raw,
        kind="invalid_format",
        resolution="fix_format",
    )


def _attachment_resolution(raw: str) -> Resolution:
    if (
        "nie istnieje" in raw
        or "nie jest poprawnym PDF" in raw
        or ("wymagany" in raw and "PDF" in raw)
    ):
        return "generate"
    if "≠" in raw:
        return "fix_format"
    return "ask_user"


def _attachment_kind(raw: str) -> IssueKind:
    if "≠" in raw or "FAKTURA" in raw or "PDF" in raw or "%%EOF" in raw:
        return "invalid_format"
    return "missing"


def _attachment_code(raw: str) -> str:
    if "nie istnieje" in raw:
        return "attachment.missing_file"
    if "kwota" in raw:
        return "attachment.amount_mismatch"
    if "%%EOF" in raw:
        return "attachment.invalid_eof"
    return "attachment.invalid_pdf"


def _other_issue(raw: str) -> ValidationIssue:
    return ValidationIssue(
        code="validation.other",
        field_name="",
        message=raw,
        kind="mismatch",
        resolution="ask_user",
    )
