"""Format and enrich attachment_validation on chat responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .doql_context import resolve_doql_context_path
from .path_resolve import resolve_attachment_path
from .validation.context import ValidationContext
from .validation.helpers import parse_amount
from .validation.issue import Phase, issues_to_messages
from .validation.rules.attachment import validate_attachment_path


def format_attachment_validation(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    path = str(payload.get("path") or "").strip()
    if not path:
        return None
    status = str(payload.get("status") or "unknown")
    resolved = str(payload.get("resolved") or path)
    issues = payload.get("issues") or []
    line = f"📎 Załącznik [{status}]: {path}"
    if resolved and resolved != path:
        line += f" → {resolved}"
    if issues:
        line += f" — {issues[0]}"
    return line


def build_attachment_validation(
    raw_path: str,
    *,
    action: str = "send_invoice",
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = (raw_path or "").strip()
    if not raw:
        return {"path": "", "resolved": "", "status": "skipped", "issues": []}

    doql = resolve_doql_context_path()
    resolved = resolve_attachment_path(raw, doql_path=doql)
    cfg = dict(config or {})
    cfg.setdefault("attachment_path", raw)

    vctx = ValidationContext(
        phase=Phase.POST_EXECUTE,
        action=action,
        config=cfg,
        path_resolver=lambda p: resolve_attachment_path(p, doql_path=doql),
    )
    issue_msgs = issues_to_messages(
        validate_attachment_path(vctx, raw, expected_amount=parse_amount(cfg.get("amount")))
    )

    status = "ok"
    if not Path(resolved).is_file():
        status = "missing"
        if not any("nie istnieje" in m for m in issue_msgs):
            issue_msgs.append(f"attachment_path: plik nie istnieje: {raw}")
    elif issue_msgs:
        status = "invalid"

    return {"path": raw, "resolved": resolved, "status": status, "issues": issue_msgs}


def _attachment_from_dsl(dsl: Mapping[str, Any]) -> dict[str, Any] | None:
    for step in dsl.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        config = dict(step.get("config") or {})
        raw = str(config.get("attachment_path") or "").strip()
        if raw:
            return build_attachment_validation(raw, action=action, config=config)
    return None


def _prefer_local_validation(
    remote: dict[str, Any],
    local: dict[str, Any] | None,
) -> dict[str, Any]:
    if local and remote.get("status") == "ok" and local.get("status") != "ok":
        return local
    return remote


def _apply_attachment_to_execution(
    execution: dict[str, Any],
    av: dict[str, Any],
) -> None:
    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_result = step.setdefault("result", {})
        if not isinstance(step_result, dict):
            continue
        step_result["attachment_validation"] = av
        if av.get("status") != "ok" and step_result.get("attachment_used") is True:
            step_result["attachment_used"] = False
        break


def enrich_chat_response(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure attachment_validation is on response (API may omit it on older services)."""
    execution = data.get("execution") or {}
    local_av = _attachment_from_dsl(data.get("dsl") or {})

    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_result = step.get("result") or {}
        if isinstance(step_result, dict) and step_result.get("attachment_validation"):
            av = _prefer_local_validation(step_result["attachment_validation"], local_av)
            step_result["attachment_validation"] = av
            data["attachment_validation"] = av
            return av

    if data.get("attachment_validation"):
        av = _prefer_local_validation(data["attachment_validation"], local_av)
        data["attachment_validation"] = av
        return av

    if local_av:
        data["attachment_validation"] = local_av
        _apply_attachment_to_execution(execution, local_av)
        return local_av
    return {}
