"""Shared helpers for run-conversation-scenario.py."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def wait_health(base_url: str, timeout_s: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout_s
    url = f"{base_url.rstrip('/')}/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(url), timeout=5) as resp:
                if resp.status == 200:
                    return True
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(2)
    return False


def _dsl_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    dsl = payload.get("dsl") or payload.get("partial_workflow")
    return dsl if isinstance(dsl, dict) else None


def dsl_actions(response: dict[str, Any]) -> list[str]:
    dsl = _dsl_from_payload(response)
    if dsl is None:
        return []
    return [str(s.get("action", "")) for s in dsl.get("steps") or [] if isinstance(s, dict)]


def workflow_execution_payload(response: dict[str, Any]) -> dict[str, Any] | None:
    execution = response.get("execution")
    if isinstance(execution, dict):
        return execution
    inner = response.get("result")
    return inner if isinstance(inner, dict) else None


def execution_completed(response: dict[str, Any]) -> bool:
    execution = workflow_execution_payload(response)
    if execution is None:
        return False
    if execution.get("status") == "completed":
        return True
    steps = execution.get("steps") or []
    return bool(steps) and all(
        isinstance(s, dict) and s.get("status") == "completed" for s in steps
    )


def _check_status(response: dict[str, Any], expect: dict[str, Any]) -> str | None:
    status = str(response.get("status", ""))
    if "status" in expect and status != expect["status"]:
        return f"expected status={expect['status']!r}, got {status!r}"
    if "status_in" in expect:
        allowed = [str(s) for s in expect["status_in"]]
        if status not in allowed:
            return f"expected status in {allowed}, got {status!r}"
    return None


def _check_missing(response: dict[str, Any], expect: dict[str, Any]) -> str | None:
    if "missing_any" not in expect:
        return None
    missing = [str(m) for m in response.get("missing") or []]
    wanted = [str(m) for m in expect["missing_any"]]
    if not any(
        w in missing or any(m.endswith(f".{w}") or m == w for m in missing)
        for w in wanted
    ):
        return f"expected missing any of {wanted}, got {missing}"
    return None


def _check_dsl_actions(response: dict[str, Any], expect: dict[str, Any]) -> str | None:
    actions = dsl_actions(response)
    if "dsl_action" in expect:
        action = str(expect["dsl_action"])
        if action not in actions:
            return f"expected dsl action {action!r}, got {actions}"
    if "dsl_action_any" in expect:
        wanted = [str(a) for a in expect["dsl_action_any"]]
        if not any(a in actions for a in wanted):
            return f"expected any dsl action in {wanted}, got {actions}"
    return None


def _check_routing_and_autofill(response: dict[str, Any], expect: dict[str, Any]) -> str | None:
    if expect.get("execution_completed") and not execution_completed(response):
        return "expected completed execution"
    routing = response.get("routing") or {}
    if "routing_source" in expect:
        source = str(routing.get("source") or "")
        wanted = str(expect["routing_source"])
        if wanted not in source:
            return f"expected routing source {wanted!r}, got {source!r}"
    if "autofill_any" in expect:
        applied = [str(a) for a in response.get("autofill_applied") or []]
        wanted = [str(w) for w in expect["autofill_any"]]
        if not any(
            w in applied or any(a.endswith(f".{w}") or a == w for a in applied)
            for w in wanted
        ):
            return f"expected autofill any of {wanted}, got {applied}"
    return None


def check_expect(response: dict[str, Any], expect: dict[str, Any]) -> tuple[bool, str]:
    for checker in (_check_status, _check_missing, _check_dsl_actions, _check_routing_and_autofill):
        if err := checker(response, expect):
            return False, err
    return True, "ok"


def _check_execution_routing(response: dict[str, Any], expect: dict[str, Any]) -> str | None:
    if "routing_source" not in expect:
        return None
    routing = response.get("routing") or {}
    source = str(routing.get("source") or routing.get("parser") or "")
    wanted = str(expect["routing_source"])
    if wanted not in source and source != wanted:
        return f"expected routing source {wanted!r}, got {source!r}"
    return None


def check_execution_expect(response: dict[str, Any], expect: dict[str, Any]) -> tuple[bool, str]:
    for checker in (_check_status, _check_dsl_actions, _check_routing_and_autofill, _check_execution_routing):
        if err := checker(response, expect):
            return False, err
    return True, "ok"


def run_validation(v: dict[str, Any], last_response: dict[str, Any]) -> dict[str, Any]:
    from dsl_validate.profile_checks import (
        ProfileCheckContext,
        parse_profile_validation,
        run_profile_validation_checks,
    )

    spec = parse_profile_validation(v)
    if spec is None:
        vid = str(v.get("id", v.get("type", "validation")))
        return {"id": vid, "passed": False, "summary": f"unknown validation entry {v!r}"}
    results = run_profile_validation_checks([spec], ProfileCheckContext(response=last_response))
    return results[0]


def prepare_doql_context(scenario_path: Path, scenario: dict[str, Any]) -> None:
    doql_rel = scenario.get("doql_context")
    if not doql_rel:
        return
    from nlp2dsl_artifacts import collect_environment
    from env2llm.doql_context import collect_task_context, write_doql_context

    example_dir = scenario_path.parent.parent
    doql_path = (scenario_path.parent / str(doql_rel)).resolve()
    if doql_path.is_file():
        os.environ["NLP2DSL_DOQL_CONTEXT"] = str(doql_path)
        return

    ctx = collect_task_context(
        example_dir,
        example_name=str(scenario.get("example_id", example_dir.name)),
        environment=collect_environment(),
    )
    if "attachment" in scenario_path.name:
        ctx.attachment_required = True
        ctx.generate_invoice_if_missing = False
        ctx.data.pop("send_invoice.attachment_path", None)
        ctx.capabilities = ["send_invoice", "generate_invoice"]
    write_doql_context(doql_path, ctx)
    os.environ["NLP2DSL_DOQL_CONTEXT"] = str(doql_path)


def run_turn(flow: Any, turn: dict[str, Any], *, idx: int) -> dict[str, Any]:
    text = str(turn.get("text", "")).strip()
    if idx == 1:
        return flow.start(text)
    inline = turn.get("context_inline")
    if inline:
        response = flow.client.chat_message(
            flow.conversation_id or "",
            text,
            context_inline=inline,
        )
        flow.history.append({"role": "user", "text": text})
        flow._record_turn("user", text, "/workflow/chat/message", response)
        flow._handle_response(response)
        return response
    return flow.send_message(text)


def turn_loop_action(flow: Any, turn: dict[str, Any], *, idx: int) -> str | None:
    """Return 'continue', 'break', or None for the next turn iteration."""
    if flow._last_response.get("status") == "executed" and turn.get("optional_if_executed"):
        return "continue"
    if flow._last_response.get("status") == "executed" and idx > 1 and not turn.get("optional_if_executed"):
        return "break"
    return None


def finalize_trace(
    flow: Any,
    *,
    scenario_path: Path,
    scenario: dict[str, Any],
    turn_errors: list[str],
    validations: list[dict[str, Any]],
) -> dict[str, Any]:
    trace = flow.export_trace()
    trace["scenario"] = scenario_path.name
    trace["example_id"] = scenario.get("example_id", scenario_path.parent.parent.name)
    trace["generated_at"] = datetime.now(timezone.utc).isoformat()
    trace["validations"] = validations
    trace["passed"] = not turn_errors and all(v.get("passed") for v in validations)
    trace["errors"] = turn_errors
    return trace
