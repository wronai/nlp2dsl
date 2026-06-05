#!/usr/bin/env python3
"""Run execution.scenario.yaml (one-shot NLP → DSL → execute) against live nlp2dsl."""

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


def _dsl_actions(result: dict[str, Any]) -> list[str]:
    dsl = result.get("dsl") or result.get("partial_workflow")
    if not isinstance(dsl, dict):
        return []
    return [str(s.get("action", "")) for s in dsl.get("steps") or [] if isinstance(s, dict)]


def _execution_completed(result: dict[str, Any]) -> bool:
    execution = result.get("result") or result.get("execution")
    if not isinstance(execution, dict):
        return False
    if execution.get("status") == "completed":
        return True
    steps = execution.get("steps") or []
    return bool(steps) and all(
        isinstance(s, dict) and s.get("status") == "completed" for s in steps
    )


def _check_expect(result: dict[str, Any], expect: dict[str, Any]) -> tuple[bool, str]:
    status = str(result.get("status", ""))
    if "status" in expect and status != expect["status"]:
        return False, f"expected status={expect['status']!r}, got {status!r}"
    if "status_in" in expect:
        allowed = [str(s) for s in expect["status_in"]]
        if status not in allowed:
            return False, f"expected status in {allowed}, got {status!r}"
    if "dsl_action" in expect:
        action = str(expect["dsl_action"])
        if action not in _dsl_actions(result):
            return False, f"expected dsl action {action!r}, got {_dsl_actions(result)}"
    if expect.get("execution_completed") and not _execution_completed(result):
        return False, "expected completed execution"
    routing = result.get("routing") or {}
    if "routing_source" in expect:
        source = str(routing.get("source") or routing.get("parser") or "")
        wanted = str(expect["routing_source"])
        if wanted not in source and source != wanted:
            return False, f"expected routing source {wanted!r}, got {source!r}"
    return True, "ok"


def _run_validation(v: dict[str, Any], last: dict[str, Any]) -> dict[str, Any]:
    vid = str(v.get("id", v.get("type", "validation")))
    vtype = str(v.get("type", ""))
    if vtype == "dsl_action":
        action = str(v.get("action", ""))
        passed = action in _dsl_actions(last)
        return {"id": vid, "passed": passed, "summary": f"dsl action {action!r}" if passed else f"missing {action!r}"}
    if vtype == "execution_completed":
        passed = _execution_completed(last)
        return {"id": vid, "passed": passed, "summary": "execution completed" if passed else "execution incomplete"}
    return {"id": vid, "passed": False, "summary": f"unknown type {vtype!r}"}


def run_scenario(
    scenario_path: Path,
    *,
    base_url: str,
    artifact_root: Path | None = None,
    wait_health: bool = True,
) -> dict[str, Any]:
    from nlp2dsl_sdk.client import NLP2DSLClient

    scenario = _load_yaml(scenario_path)
    if wait_health and not _wait_health(base_url):
        raise RuntimeError(f"nlp2dsl not healthy at {base_url}")

    client = NLP2DSLClient(backend_url=base_url)
    queries_out: list[dict[str, Any]] = []
    errors: list[str] = []
    last_result: dict[str, Any] = {}

    for idx, q in enumerate(scenario.get("queries") or [], start=1):
        text = str(q.get("query", "")).strip()
        if not text:
            errors.append(f"query {idx}: empty")
            continue
        mode = str(q.get("mode") or scenario.get("nlp_mode") or "auto")
        execute = bool(q.get("execute", True))
        try:
            result = client.workflow_from_text(text, execute=execute, mode=mode)
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}
        last_result = result
        entry = {"query": text, "mode": mode, "execute": execute, "result": result}
        queries_out.append(entry)
        expect = q.get("expect") or {}
        if expect:
            ok, msg = _check_expect(result, expect)
            if not ok:
                errors.append(f"query {idx}: {msg}")

    validations = [_run_validation(v, last_result) for v in scenario.get("validations") or [] if isinstance(v, dict)]
    trace = {
        "example_id": scenario.get("example_id", scenario_path.parent.parent.name),
        "scenario": scenario_path.name,
        "nlp_mode": scenario.get("nlp_mode", "auto"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries": queries_out,
        "validations": validations,
        "errors": errors,
        "passed": not errors and all(v.get("passed") for v in validations),
        "status": last_result.get("status"),
    }

    out_root = artifact_root or scenario_path.parent
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "execution.trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    scenario_path = args.scenario.resolve()
    if not scenario_path.is_file():
        print(f"Missing: {scenario_path}", file=sys.stderr)
        return 2

    try:
        trace = run_scenario(scenario_path, base_url=args.base_url, wait_health=not args.no_wait)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(trace, indent=2, ensure_ascii=False))
    else:
        status = "PASSED" if trace.get("passed") else "FAILED"
        print(f"{status}: {scenario_path.name} — last_status={trace.get('status')}")
        for err in trace.get("errors") or []:
            print(f"  - {err}", file=sys.stderr)

    return 0 if trace.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
