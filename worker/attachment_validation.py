"""Worker attachment validation — SDK validation adapter (B1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nlp2dsl_sdk.validation.issue import Phase
from path_resolve import resolve_worker_attachment_path
from step_validator import validate_step_config_issues


def build_attachment_validation(
    raw_path: str,
    *,
    action: str = "send_invoice",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve + validate attachment via SDK step validation (POST_EXECUTE phase)."""
    raw = str(raw_path or "").strip()
    if not raw:
        return {"path": "", "resolved": "", "status": "skipped", "issues": []}

    resolved = resolve_worker_attachment_path(raw)
    cfg = dict(config or {})
    cfg.setdefault("attachment_path", raw)
    step_issues = validate_step_config_issues(action, cfg, phase=Phase.POST_EXECUTE)
    attachment_issues = [
        i.to_legacy_message()
        for i in step_issues
        if i.field_name == "attachment_path" or i.code.startswith("attachment.")
    ]

    status = "ok"
    if not Path(resolved).is_file():
        status = "missing"
        if not any("nie istnieje" in i for i in attachment_issues):
            attachment_issues.append(f"attachment_path: plik nie istnieje: {raw}")
    elif attachment_issues:
        status = "invalid"

    return {"path": raw, "resolved": resolved, "status": status, "issues": attachment_issues}


def validate_invoice_attachment(raw_path: str, config: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible wrapper for send_invoice attachment checks."""
    return build_attachment_validation(raw_path, action="send_invoice", config=config)
