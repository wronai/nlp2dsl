"""Step validation using SystemMapIR (SDK-side, mirrors nlp-service validator)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .system_map_ir import SystemMapIR
from .path_resolve import resolve_attachment_path
from .doql_context import resolve_doql_context_path


def _is_empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def _parse_amount(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _validate_pdf_attachment(path_str: str, *, expected_amount: float | None) -> list[str]:
    import os

    doql = resolve_doql_context_path()
    resolved = resolve_attachment_path(path_str, doql_path=doql)
    path = Path(resolved)
    if not path.is_file():
        return [f"attachment_path: plik nie istnieje: {path_str}"]

    try:
        head = path.read_bytes()[:5]
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    if head.startswith(b"%PDF"):
        return []

    strict = os.environ.get("NLP2DSL_STRICT_PDF", "").strip().lower() in ("1", "true", "yes")
    if strict:
        return ["attachment_path: wymagany binarny PDF (%PDF), a plik nim nie jest"]

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    issues: list[str] = []
    if not text.strip().startswith("FAKTURA"):
        issues.append(
            "attachment_path: plik nie jest poprawnym PDF (%PDF) ani fakturą MVP (nagłówek FAKTURA)"
        )
        return issues

    if expected_amount is not None:
        match = re.search(r"Kwota:\s*([\d.]+)", text)
        if not match:
            issues.append("attachment_path: brak kwoty w pliku tekstowym faktury")
        elif abs(float(match.group(1)) - expected_amount) > 0.01:
            issues.append(
                f"attachment_path: kwota w pliku ({float(match.group(1))}) ≠ w request ({expected_amount})"
            )
    return issues


def validate_step_config_from_map(
    ir: SystemMapIR,
    action: str,
    config: dict[str, Any] | None,
) -> list[str]:
    """Validate one step config against SystemMapIR + format rules."""
    config = dict(config or {})
    issues: list[str] = []

    cmd = ir.command(action)
    if cmd is None:
        return [f"unknown_action:{action}"]

    missing = ir.validate_step_config(action, config)
    for field in missing:
        issues.append(f"brak wymaganego pola: {field}")

    if ir.conversation.attachment_required and action == "send_invoice":
        if _is_empty(config.get("attachment_path")):
            issues.append("brak attachment_path (conversation.attachment_required)")

    amount = _parse_amount(config.get("amount"))
    to_val = config.get("to")
    if not _is_empty(to_val) and isinstance(to_val, str) and "@" not in to_val:
        issues.append(f"to: nie wygląda na adres email: {to_val}")

    if amount is None and "amount" in config and not _is_empty(config.get("amount")):
        issues.append(f"amount: nie jest liczbą: {config.get('amount')!r}")

    attachment = config.get("attachment_path")
    if not _is_empty(attachment) and isinstance(attachment, str):
        issues.extend(_validate_pdf_attachment(attachment, expected_amount=amount))

    return issues


def validate_workflow_from_map(ir: SystemMapIR, steps: list[Any]) -> list[tuple[int, str, list[str]]]:
    failures: list[tuple[int, str, list[str]]] = []
    for index, step in enumerate(steps):
        action = getattr(step, "action", None) or (step.get("action") if isinstance(step, dict) else None)
        config = getattr(step, "config", None) or (step.get("config") if isinstance(step, dict) else {}) or {}
        if not action:
            failures.append((index, "?", ["brak action w kroku workflow"]))
            continue
        issues = validate_step_config_from_map(ir, str(action), dict(config))
        if issues:
            failures.append((index, str(action), issues))
    return failures
