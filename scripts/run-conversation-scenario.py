#!/usr/bin/env python3
"""Run a conversation.scenario.yaml against live nlp2dsl (Docker) and write trace artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _wait_health(base_url: str, timeout_s: float = 120.0) -> bool:
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


def _dsl_actions(response: dict[str, Any]) -> list[str]:
    dsl = response.get("dsl")
    if not isinstance(dsl, dict):
        return []
    return [str(s.get("action", "")) for s in dsl.get("steps") or [] if isinstance(s, dict)]


def _execution_completed(response: dict[str, Any]) -> bool:
    execution = response.get("execution")
    if not isinstance(execution, dict):
        return False
    if execution.get("status") == "completed":
        return True
    steps = execution.get("steps") or []
    return bool(steps) and all(
        isinstance(s, dict) and s.get("status") == "completed" for s in steps
    )


def _check_expect(response: dict[str, Any], expect: dict[str, Any]) -> tuple[bool, str]:
    status = str(response.get("status", ""))
    if "status" in expect and status != expect["status"]:
        return False, f"expected status={expect['status']!r}, got {status!r}"
    if "status_in" in expect:
        allowed = [str(s) for s in expect["status_in"]]
        if status not in allowed:
            return False, f"expected status in {allowed}, got {status!r}"
    missing = [str(m) for m in response.get("missing") or []]
    if "missing_any" in expect:
        wanted = [str(m) for m in expect["missing_any"]]
        if not any(
            w in missing or any(m.endswith(f".{w}") or m == w for m in missing)
            for w in wanted
        ):
            return False, f"expected missing any of {wanted}, got {missing}"
    if "dsl_action" in expect:
        action = str(expect["dsl_action"])
        if action not in _dsl_actions(response):
            return False, f"expected dsl action {action!r}, got {_dsl_actions(response)}"
    if "dsl_action_any" in expect:
        wanted = [str(a) for a in expect["dsl_action_any"]]
        actions = _dsl_actions(response)
        if not any(a in actions for a in wanted):
            return False, f"expected any dsl action in {wanted}, got {actions}"
    if expect.get("execution_completed") and not _execution_completed(response):
        return False, "expected completed execution"
    routing = response.get("routing") or {}
    if "routing_source" in expect:
        source = str(routing.get("source") or "")
        wanted = str(expect["routing_source"])
        if wanted not in source:
            return False, f"expected routing source {wanted!r}, got {source!r}"
    if "autofill_any" in expect:
        applied = [str(a) for a in response.get("autofill_applied") or []]
        wanted = [str(w) for w in expect["autofill_any"]]
        if not any(
            w in applied or any(a.endswith(f".{w}") or a == w for a in applied)
            for w in wanted
        ):
            return False, f"expected autofill any of {wanted}, got {applied}"
    return True, "ok"


def _run_validation(v: dict[str, Any], last_response: dict[str, Any]) -> dict[str, Any]:
    vid = str(v.get("id", v.get("type", "validation")))
    vtype = str(v.get("type", ""))
    if vtype == "dsl_action":
        action = str(v.get("action", ""))
        passed = action in _dsl_actions(last_response)
        return {
            "id": vid,
            "passed": passed,
            "summary": f"dsl action {action!r} present" if passed else f"missing action {action!r}",
        }
    if vtype == "execution_completed":
        passed = _execution_completed(last_response)
        return {
            "id": vid,
            "passed": passed,
            "summary": "execution completed" if passed else "execution not completed",
        }
    return {"id": vid, "passed": False, "summary": f"unknown validation type {vtype!r}"}


def run_scenario(
    scenario_path: Path,
    *,
    base_url: str,
    artifact_root: Path | None = None,
    wait_health: bool = True,
) -> dict[str, Any]:
    import os

    from nlp2dsl_sdk.artifacts import collect_environment
    from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient
    from nlp2dsl_sdk.conversation_artifacts import write_conversation_artifacts
    from nlp2dsl_sdk.doql_context import collect_task_context, write_doql_context

    scenario = _load_yaml(scenario_path)
    example_dir = scenario_path.parent.parent
    os.environ.setdefault("NLP2DSL_EXAMPLE_DIR", str(example_dir))

    doql_rel = scenario.get("doql_context")
    attachment_mode = "attachment" in scenario_path.name
    if doql_rel:
        doql_path = (scenario_path.parent / str(doql_rel)).resolve()
        if not doql_path.is_file():
            ctx = collect_task_context(
                example_dir,
                example_name=str(scenario.get("example_id", example_dir.name)),
                environment=collect_environment(),
            )
            if attachment_mode:
                ctx.attachment_required = True
                ctx.generate_invoice_if_missing = False
                ctx.data.pop("send_invoice.attachment_path", None)
                ctx.capabilities = ["send_invoice", "generate_invoice"]
            write_doql_context(doql_path, ctx)
        os.environ["NLP2DSL_DOQL_CONTEXT"] = str(doql_path)

    if wait_health and not _wait_health(base_url):
        raise RuntimeError(f"nlp2dsl not healthy at {base_url}")

    flow = ConversationFlow(NLP2DSLClient(backend_url=base_url))

    turn_errors: list[str] = []
    for idx, turn in enumerate(scenario.get("turns") or [], start=1):
        text = str(turn.get("text", "")).strip()
        if not text:
            turn_errors.append(f"turn {idx}: empty text")
            continue
        if flow._last_response.get("status") == "executed" and turn.get("optional_if_executed"):
            continue
        if flow._last_response.get("status") == "executed" and idx > 1 and not turn.get("optional_if_executed"):
            break
        if idx == 1:
            response = flow.start(text)
        else:
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
            else:
                response = flow.send_message(text)
        expect = turn.get("expect") or {}
        if expect:
            ok, msg = _check_expect(response, expect)
            if not ok:
                turn_errors.append(f"turn {idx}: {msg}")

    validations: list[dict[str, Any]] = []
    for v in scenario.get("validations") or []:
        if isinstance(v, dict):
            validations.append(_run_validation(v, flow._last_response))

    trace = flow.export_trace()
    trace["scenario"] = scenario_path.name
    trace["example_id"] = scenario.get("example_id", scenario_path.parent.parent.name)
    trace["generated_at"] = datetime.now(timezone.utc).isoformat()
    trace["validations"] = validations
    trace["passed"] = not turn_errors and all(v.get("passed") for v in validations)
    trace["errors"] = turn_errors

    out_root = artifact_root or scenario_path.parent
    scenario_cfg = _load_yaml(scenario_path)
    trace_name = "conversation.llm.trace.json" if scenario_cfg.get("record_llm_routing") else "conversation.trace.json"
    write_conversation_artifacts(out_root, trace, scenario_name=scenario_path.name)
    # rename if llm variant (write_conversation_artifacts always writes conversation.trace.json)
    if trace_name != "conversation.trace.json":
        src = out_root / "conversation.trace.json"
        dst = out_root / trace_name
        if src.is_file():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    return trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="Path to conversation.scenario.yaml")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--no-wait", action="store_true", help="Skip health wait")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    scenario_path = args.scenario.resolve()
    if not scenario_path.is_file():
        print(f"Missing scenario: {scenario_path}", file=sys.stderr)
        return 2

    try:
        trace = run_scenario(
            scenario_path,
            base_url=args.base_url,
            wait_health=not args.no_wait,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(trace, indent=2, ensure_ascii=False))
    else:
        status = "PASSED" if trace.get("passed") else "FAILED"
        print(f"{status}: {scenario_path} — conversation_id={trace.get('conversation_id')}")
        for err in trace.get("errors") or []:
            print(f"  - {err}", file=sys.stderr)
        for v in trace.get("validations") or []:
            mark = "ok" if v.get("passed") else "FAIL"
            print(f"  [{mark}] {v.get('id')}: {v.get('summary')}")

    return 0 if trace.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
