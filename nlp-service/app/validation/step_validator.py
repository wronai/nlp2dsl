"""Validate step config (required fields + formats) before the next process step."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.conversation.system_map import get_doql_context
from app.registry import ACTIONS_REGISTRY, get_quality_required_fields, get_required_fields
from app.validation.path_resolve import resolve_attachment_path


class StepValidationError(Exception):
    def __init__(self, action: str, issues: list[str]) -> None:
        self.action = action
        self.issues = issues
        super().__init__(f"{action}: {'; '.join(issues)}")


def _is_empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def _parse_amount(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _validate_pdf_attachment(path_str: str, *, expected_amount: float | None) -> list[str]:
    issues: list[str] = []
    from app.conversation.doql_context import resolve_doql_context_path

    doql = resolve_doql_context_path()
    resolved = resolve_attachment_path(path_str, doql_path=doql)
    path = Path(resolved)
    if not path.is_file():
        return [
            f"attachment_path: plik nie istnieje: {path_str}"
            + (f" (resolved: {resolved})" if resolved != path_str else "")
        ]

    try:
        head = path.read_bytes()[:5]
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    if head.startswith(b"%PDF"):
        return issues

    strict = os.environ.get("NLP2DSL_STRICT_PDF", "").strip().lower() in ("1", "true", "yes")
    if strict:
        issues.append("attachment_path: wymagany binarny PDF (%PDF), a plik nim nie jest")
        return issues

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    if not text.strip().startswith("FAKTURA"):
        issues.append(
            "attachment_path: plik nie jest poprawnym PDF (%PDF) ani fakturą MVP (nagłówek FAKTURA)"
        )
        return issues

    if expected_amount is not None:
        match = re.search(r"Kwota:\s*([\d.]+)", text)
        if not match:
            issues.append("attachment_path: brak kwoty w pliku tekstowym faktury")
        else:
            file_amount = float(match.group(1))
            if abs(file_amount - expected_amount) > 0.01:
                issues.append(
                    f"attachment_path: kwota w pliku ({file_amount}) ≠ w request ({expected_amount})"
                )

    return issues


def _field_format_issues(action: str, field: str, value: Any, config: dict[str, Any]) -> list[str]:
    if _is_empty(value):
        return []

    if field == "attachment_path" and isinstance(value, str):
        return _validate_pdf_attachment(value, expected_amount=_parse_amount(config.get("amount")))

    if field == "to" and isinstance(value, str) and "@" not in value:
        return [f"to: nie wygląda na adres email: {value}"]

    if field == "amount":
        if _parse_amount(value) is None:
            return [f"amount: nie jest liczbą: {value!r}"]

    if field == "body" and action == "send_email" and isinstance(value, str) and len(value.strip()) < 3:
        return ["body: treść e-maila jest zbyt krótka"]

    return []


def _required_fields(action: str) -> list[str]:
    ctx = get_doql_context()
    if ctx is not None:
        doql_required = ctx.required_fields_for(action)
        if doql_required:
            return list(doql_required)
    return get_required_fields(action)


def validate_step_config(action: str, config: dict[str, Any] | None) -> list[str]:
    """Return validation issue messages (empty list = OK)."""
    config = dict(config or {})
    issues: list[str] = []

    if action not in ACTIONS_REGISTRY:
        return [f"unknown_action:{action}"]

    for req in _required_fields(action):
        if _is_empty(config.get(req)):
            issues.append(f"brak wymaganego pola: {req}")

    ctx = get_doql_context()
    if ctx is not None and ctx.attachment_required and action == "send_invoice":
        if _is_empty(config.get("attachment_path")):
            issues.append("brak attachment_path (conversation.attachment_required)")

    for qf in get_quality_required_fields(action):
        if _is_empty(config.get(qf)):
            issues.append(f"brak pola jakości: {qf}")

    meta = ACTIONS_REGISTRY[action]
    field_names = set(config.keys()) | set(_required_fields(action)) | set(meta.get("optional", {}))
    for field in sorted(field_names):
        if field.startswith("_"):
            continue
        val = config.get(field)
        if not _is_empty(val):
            issues.extend(_field_format_issues(action, field, val, config))

    return issues


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
