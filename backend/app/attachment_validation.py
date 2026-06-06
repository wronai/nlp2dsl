"""Attachment validation — shared by backend chat router."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.path_resolve import resolve_attachment_path
from app.step_validator import validate_step_config_issues
from nlp2dsl_sdk.validation.issue import Phase
from nlp2dsl_sdk.validation.pipeline import validate_post_execute_execution

AttachmentStatus = Literal["ok", "missing", "invalid", "denied", "skipped"]


def build_attachment_validation(
    raw_path: str,
    *,
    action: str = "send_invoice",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = (raw_path or "").strip()
    if not raw:
        return {"path": "", "resolved": "", "status": "skipped", "issues": []}

    resolved = resolve_attachment_path(raw)
    cfg = dict(config or {})
    cfg.setdefault("attachment_path", raw)
    step_issues = validate_step_config_issues(action, cfg, phase=Phase.POST_EXECUTE)
    attachment_issues = [
        i.to_legacy_message() for i in step_issues if i.field_name == "attachment_path" or i.code.startswith("attachment.")
    ]

    status: AttachmentStatus = "ok"
    if not Path(resolved).is_file():
        status = "missing"
        if not any("nie istnieje" in i for i in attachment_issues):
            attachment_issues.append(f"attachment_path: plik nie istnieje: {raw}")
    elif attachment_issues:
        status = "invalid"

    return {
        "path": raw,
        "resolved": resolved,
        "status": status,
        "issues": attachment_issues,
    }


def _top_level_attachment_validation(result: dict[str, Any]) -> dict[str, Any] | None:
    av = result.get("attachment_validation")
    return av if isinstance(av, dict) else None


def _execution_attachment_validation(execution: dict[str, Any]) -> dict[str, Any] | None:
    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_result = step.get("result") or {}
        if not isinstance(step_result, dict):
            continue
        av = step_result.get("attachment_validation")
        if isinstance(av, dict):
            return av
    return None


def _attachment_from_dsl(dsl: dict[str, Any]) -> dict[str, Any] | None:
    for step in dsl.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        config = dict(step.get("config") or {})
        raw = str(config.get("attachment_path") or "").strip()
        if raw:
            return build_attachment_validation(raw, action=action, config=config)
    return None


def validation_from_chat_result(result: dict[str, Any]) -> dict[str, Any] | None:
    """Build attachment_validation from chat/execute payload when worker omitted it."""
    return (
        _top_level_attachment_validation(result)
        or _execution_attachment_validation(result.get("execution") or {})
        or _attachment_from_dsl(result.get("dsl") or {})
    )


def ensure_attachment_validation(result: dict[str, Any]) -> None:
    """Attach validation to top-level response and execution step result (in place)."""
    # Drop stale ready-phase validation — re-validate after worker execute.
    if result.get("status") == "executed":
        result.pop("attachment_validation", None)

    execution = result.get("execution") or {}
    if isinstance(execution, dict) and execution.get("steps"):
        outcome_issues = validate_post_execute_execution(
            execution,
            dsl=result.get("dsl") if isinstance(result.get("dsl"), dict) else None,
            path_resolver=resolve_attachment_path,
        )
        if outcome_issues:
            result.setdefault("validation_issues", [])
            result["validation_issues"].extend(
                i.to_dict() for i in outcome_issues
            )

    av = validation_from_chat_result(result)
    if not av:
        return
    result["attachment_validation"] = av

    execution = result.get("execution") or {}
    steps = execution.get("steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_result = step.setdefault("result", {})
        if isinstance(step_result, dict):
            step_result["attachment_validation"] = av
            if av.get("status") != "ok" and step_result.get("attachment_used") is True:
                step_result["attachment_used"] = False
        break
