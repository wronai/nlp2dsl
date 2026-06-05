"""Validate workflow step config before execution (registry + format checks)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.path_resolve import resolve_attachment_path

# Mirror of nlp-service ACTIONS_REGISTRY subset used at execution time.
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


def _is_empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def _parse_amount(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _validate_attachment(path_str: str, *, expected_amount: float | None) -> list[str]:
    resolved = resolve_attachment_path(path_str)
    path = Path(resolved)
    if not path.is_file():
        return [f"attachment_path: plik nie istnieje: {path_str}"]

    try:
        head = path.read_bytes()[:5]
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    if head.startswith(b"%PDF"):
        return []

    if os.environ.get("NLP2DSL_STRICT_PDF", "").strip().lower() in ("1", "true", "yes"):
        return ["attachment_path: wymagany binarny PDF (%PDF)"]

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"attachment_path: nie można odczytać pliku: {exc}"]

    issues: list[str] = []
    if not text.strip().startswith("FAKTURA"):
        issues.append("attachment_path: plik nie jest poprawnym PDF ani fakturą MVP")
        return issues

    if expected_amount is not None:
        match = re.search(r"Kwota:\s*([\d.]+)", text)
        if not match:
            issues.append("attachment_path: brak kwoty w pliku faktury")
        elif abs(float(match.group(1)) - expected_amount) > 0.01:
            issues.append("attachment_path: kwota w pliku ≠ kwota w request")
    return issues


def validate_step_config(action: str, config: dict[str, Any] | None) -> list[str]:
    config = dict(config or {})
    issues: list[str] = []

    for req in _REQUIRED.get(action, []):
        if _is_empty(config.get(req)):
            issues.append(f"brak wymaganego pola: {req}")

    for qf in _QUALITY.get(action, []):
        if _is_empty(config.get(qf)):
            issues.append(f"brak pola jakości: {qf}")

    amount = _parse_amount(config.get("amount"))
    if amount is None and "amount" in config and not _is_empty(config.get("amount")):
        issues.append(f"amount: nie jest liczbą: {config.get('amount')!r}")

    to_val = config.get("to")
    if not _is_empty(to_val) and isinstance(to_val, str) and "@" not in to_val:
        issues.append(f"to: nie wygląda na adres email: {to_val}")

    attachment = config.get("attachment_path")
    if not _is_empty(attachment) and isinstance(attachment, str):
        raw = resolve_attachment_path(attachment)
        if raw != attachment:
            config["attachment_path"] = raw
        issues.extend(_validate_attachment(raw, expected_amount=amount))

    return issues
