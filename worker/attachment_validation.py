"""Worker attachment validation — SDK validation rules (no DOQL yaml deps)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nlp2dsl_sdk.path_resolve import resolve_attachment_path
from nlp2dsl_sdk.validation.context import ValidationContext
from nlp2dsl_sdk.validation.helpers import parse_amount
from nlp2dsl_sdk.validation.issue import Phase, issues_to_messages
from nlp2dsl_sdk.validation.rules.attachment import validate_attachment_path


def resolve_worker_attachment_path(raw: str) -> str:
    """Resolve attachment path using worker env (examples mount + fixtures)."""
    if not raw:
        return raw
    path = Path(raw)
    if path.is_file():
        return str(path.resolve())

    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        ex = Path(example_dir)
        for candidate in (ex / raw, ex / "fixtures" / path.name):
            if candidate.is_file():
                return str(candidate.resolve())

    os.environ.setdefault("NLP2DSL_EXAMPLES_MOUNT", "/examples")
    return resolve_attachment_path(raw)


def validate_invoice_attachment(raw_path: str, config: dict[str, Any]) -> dict[str, Any]:
    """Resolve + validate invoice PDF via shared SDK attachment rules."""
    raw = str(raw_path or "").strip()
    if not raw:
        return {"path": "", "resolved": "", "status": "skipped", "issues": []}

    resolved = resolve_worker_attachment_path(raw)
    ctx = ValidationContext(
        phase=Phase.POST_EXECUTE,
        action="send_invoice",
        config={**dict(config or {}), "attachment_path": raw},
        path_resolver=resolve_worker_attachment_path,
    )
    issues = validate_attachment_path(
        ctx,
        raw,
        expected_amount=parse_amount(config.get("amount")),
    )
    messages = issues_to_messages(issues)

    status = "ok"
    if not Path(resolved).is_file():
        status = "missing"
        if not any("nie istnieje" in m for m in messages):
            messages.append(f"attachment_path: plik nie istnieje: {raw}")
    elif messages:
        status = "invalid"

    return {"path": raw, "resolved": resolved, "status": status, "issues": messages}
