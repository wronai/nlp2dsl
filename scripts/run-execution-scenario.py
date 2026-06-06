#!/usr/bin/env python3
"""Run execution.scenario.yaml (one-shot NLP → DSL → execute) against live nlp2dsl."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _conversation_scenario import (
    check_execution_expect,
    load_yaml,
    run_validation,
    wait_health,
)

ROOT = Path(__file__).resolve().parents[1]


def _run_query(
    client: Any,
    q: dict[str, Any],
    *,
    scenario: dict[str, Any],
    idx: int,
) -> tuple[dict[str, Any], str | None]:
    text = str(q.get("query", "")).strip()
    if not text:
        return {"status": "error", "error": "empty query"}, f"query {idx}: empty"
    mode = str(q.get("mode") or scenario.get("nlp_mode") or "auto")
    execute = bool(q.get("execute", True))
    try:
        result = client.workflow_from_text(text, execute=execute, mode=mode)
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    entry = {"query": text, "mode": mode, "execute": execute, "result": result}
    expect = q.get("expect") or {}
    if expect:
        ok, msg = check_execution_expect(result, expect)
        if not ok:
            return entry, f"query {idx}: {msg}"
    return entry, None


def run_scenario(
    scenario_path: Path,
    *,
    base_url: str,
    artifact_root: Path | None = None,
    wait_health_flag: bool = True,
) -> dict[str, Any]:
    from nlp2dsl_sdk.client import NLP2DSLClient

    scenario = load_yaml(scenario_path)
    if wait_health_flag and not wait_health(base_url):
        raise RuntimeError(f"nlp2dsl not healthy at {base_url}")

    client = NLP2DSLClient(backend_url=base_url)
    queries_out: list[dict[str, Any]] = []
    errors: list[str] = []
    last_result: dict[str, Any] = {}

    for idx, q in enumerate(scenario.get("queries") or [], start=1):
        entry, err = _run_query(client, q, scenario=scenario, idx=idx)
        queries_out.append(entry)
        last_result = entry["result"]
        if err:
            errors.append(err)

    validations = [
        run_validation(v, last_result)
        for v in scenario.get("validations") or []
        if isinstance(v, dict)
    ]
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
        json.dumps(trace, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
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
        trace = run_scenario(scenario_path, base_url=args.base_url, wait_health_flag=not args.no_wait)
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
