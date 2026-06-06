"""Structured attachment_path validation (process.paths + file + invoice PDF)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.conversation.doql_context import resolve_doql_context_path
from app.conversation.system_map import get_doql_context
from app.validation.path_policy import validate_process_path
from app.validation.path_resolve import resolve_attachment_path
from app.validation.step_validator import validate_step_config

AttachmentStatus = Literal["ok", "missing", "invalid", "denied", "skipped"]


def build_attachment_validation(
    raw_path: str,
    *,
    action: str = "send_invoice",
    config: dict[str, Any] | None = None,
    access: str = "read",
) -> dict[str, Any]:
    """
    Validate attachment_path for workflow steps.

    Returns dict: path, resolved, status, issues[] — attached to chat/execution artifacts.
    """
    raw = (raw_path or "").strip()
    if not raw:
        return {
            "path": "",
            "resolved": "",
            "status": "skipped",
            "issues": [],
        }

    doql = resolve_doql_context_path()
    resolved = resolve_attachment_path(raw, doql_path=doql)
    issues: list[str] = []
    status: AttachmentStatus = "ok"

    ctx = get_doql_context()
    if ctx is not None:
        scope_msg = validate_process_path(ctx, resolved, access=access)
        if scope_msg:
            issues.append(scope_msg)
            status = "denied"

    cfg = dict(config or {})
    cfg.setdefault("attachment_path", raw)
    step_issues = validate_step_config(action, cfg)
    attachment_issues = [i for i in step_issues if "attachment_path" in i]
    for issue in attachment_issues:
        if issue not in issues:
            issues.append(issue)

    path = Path(resolved)
    if not path.is_file():
        if status != "denied":
            status = "missing"
        if not any("nie istnieje" in i for i in issues):
            issues.append(f"attachment_path: plik nie istnieje: {raw}")
    elif attachment_issues and status == "ok":
        status = "invalid"

    return {
        "path": raw,
        "resolved": resolved,
        "status": status,
        "issues": issues,
    }
