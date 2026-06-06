#!/usr/bin/env python3
"""Start Docker stack for examples, run conversation E2E, validate nlp2dsl + services."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = ROOT / "examples" / "example-profiles.yaml"
CONV_SCRIPT = ROOT / "scripts" / "run-conversation-scenario.py"
EXEC_SCRIPT = ROOT / "scripts" / "run-execution-scenario.py"
RESULTS_SCRIPT = ROOT / "scripts" / "run-example-testql-results.py"


def _py() -> str:
    for candidate in (ROOT / ".venv/bin/python3", ROOT / "venv/bin/python3"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _load_profiles() -> dict[str, Any]:
    return yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8")) or {}


def _health_ok(base_url: str) -> bool:
    try:
        with urlopen(Request(f"{base_url.rstrip('/')}/health"), timeout=5) as resp:
            return resp.status == 200
    except (URLError, OSError, TimeoutError):
        return False


def _collect_profiles(example_ids: list[str], cfg: dict[str, Any]) -> set[str]:
    profiles: set[str] = set()
    examples = cfg.get("examples") or {}
    for eid in example_ids:
        entry = examples.get(eid) or {}
        for p in entry.get("docker_profiles") or []:
            profiles.add(str(p))
    return profiles


def docker_up(profiles: set[str], *, build: bool = False) -> None:
    cmd = [
        "docker", "compose",
        "-f", str(ROOT / "docker-compose.yml"),
        "-f", str(ROOT / "docker-compose.e2e.yml"),
    ]
    for profile in sorted(profiles):
        cmd.extend(["--profile", profile])
    cmd.append("up")
    cmd.append("-d")
    if build:
        cmd.append("--build")
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def docker_down() -> None:
    cmd = [
        "docker", "compose",
        "-f", str(ROOT / "docker-compose.yml"),
        "-f", str(ROOT / "docker-compose.e2e.yml"),
        "down", "--remove-orphans",
    ]
    subprocess.run(cmd, cwd=ROOT, check=False)


def wait_platform(base_url: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _health_ok(base_url):
            return True
        time.sleep(3)
    return False


def run_example_main(example_dir: Path) -> bool:
    main_py = example_dir / "main.py"
    if not main_py.is_file():
        return True
    proc = subprocess.run([_py(), str(main_py)], cwd=example_dir)
    return proc.returncode == 0


def run_execution(example_dir: Path, rel: str, base_url: str) -> dict[str, Any]:
    scenario = example_dir / rel
    if not scenario.is_file():
        return {"skipped": True, "reason": f"missing {rel}"}
    proc = subprocess.run(
        [_py(), str(EXEC_SCRIPT), str(scenario), "--base-url", base_url, "--no-wait"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    trace_path = example_dir / ".nlp2dsl" / "execution.trace.json"
    trace: dict[str, Any] = {}
    if trace_path.is_file():
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    trace["exit_code"] = proc.returncode
    if proc.returncode != 0 and not trace:
        trace["passed"] = False
        trace["stderr"] = proc.stderr[-2000:]
    return trace


def run_conversation(example_dir: Path, rel: str, base_url: str) -> dict[str, Any]:
    scenario = example_dir / rel
    if not scenario.is_file():
        return {"skipped": True, "reason": f"missing {rel}"}

    proc = subprocess.run(
        [_py(), str(CONV_SCRIPT), str(scenario), "--base-url", base_url, "--no-wait"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    trace_path = example_dir / ".nlp2dsl" / "conversation.trace.json"
    trace: dict[str, Any] = {}
    if trace_path.is_file():
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    trace["exit_code"] = proc.returncode
    if proc.returncode != 0 and not trace:
        trace["passed"] = False
        trace["stderr"] = proc.stderr[-2000:]
    return trace


def process_example(
    example_id: str,
    entry: dict[str, Any],
    *,
    base_url: str,
    skip_main: bool,
    run_llm: bool,
) -> dict[str, Any]:
    example_dir = ROOT / "examples" / example_id
    report: dict[str, Any] = {
        "example_id": example_id,
        "title": entry.get("title", example_id),
        "services": entry.get("services") or [],
        "docker_profiles": entry.get("docker_profiles") or [],
        "passed": True,
        "checks": [],
    }

    if entry.get("requires_llm_key") and not os.environ.get("OPENROUTER_API_KEY"):
        report["checks"].append({"id": "llm.key", "status": "skipped", "summary": "no OPENROUTER_API_KEY (set in .env or export)"})
        report["status"] = "skipped"
        report["passed"] = True
        return report

    if not skip_main:
        ok = run_example_main(example_dir)
        report["checks"].append({
            "id": "example.main",
            "status": "passed" if ok else "failed",
            "summary": "main.py" if ok else "main.py failed",
        })
        if not ok:
            report["passed"] = False

    exec_rel = entry.get("execution_scenario")
    if exec_rel:
        exec_trace = run_execution(example_dir, str(exec_rel), base_url)
        if exec_trace.get("skipped"):
            report["checks"].append({"id": "execution.e2e", "status": "skipped", "summary": exec_trace.get("reason", "")})
        else:
            passed = bool(exec_trace.get("passed")) and exec_trace.get("exit_code", 1) == 0
            report["checks"].append({
                "id": "execution.e2e",
                "status": "passed" if passed else "failed",
                "summary": f"status={exec_trace.get('status')} queries={len(exec_trace.get('queries') or [])}",
            })
            if not passed:
                report["passed"] = False

    if entry.get("conversation"):
        conv_rel = str(entry.get("conversation_scenario") or "")
        conv = run_conversation(example_dir, conv_rel, base_url)
        if conv.get("skipped"):
            report["checks"].append({"id": "conversation", "status": "skipped", "summary": conv.get("reason", "no scenario")})
        else:
            passed = bool(conv.get("passed")) and conv.get("exit_code", 1) == 0
            report["checks"].append({
                "id": "conversation.e2e",
                "status": "passed" if passed else "failed",
                "summary": f"conversation_id={conv.get('conversation_id')} status={conv.get('status')}",
                "transcript": str(example_dir / ".nlp2dsl" / "conversation.transcript.md"),
            })
            report["conversation"] = {
                "conversation_id": conv.get("conversation_id"),
                "status": conv.get("status"),
                "errors": conv.get("errors"),
                "validations": conv.get("validations"),
            }
            if not passed:
                report["passed"] = False

        if run_llm and entry.get("conversation_scenario_llm") and os.environ.get("OPENROUTER_API_KEY"):
            llm_rel = str(entry["conversation_scenario_llm"])
            llm_conv = run_conversation(example_dir, llm_rel, base_url)
            passed = bool(llm_conv.get("passed")) and llm_conv.get("exit_code", 1) == 0
            report["checks"].append({
                "id": "conversation.llm",
                "status": "passed" if passed else "failed",
                "summary": f"LLM dialog status={llm_conv.get('status')}",
                "transcript": str(example_dir / ".nlp2dsl" / "conversation.transcript.md"),
            })
            if not passed:
                report["passed"] = False

    profile_validations = entry.get("validations") or []
    if profile_validations:
        from nlp2dsl_sdk.validation.profile_checks import response_from_e2e_trace, run_validations_from_raw

        last_response: dict[str, Any] = {}
        conv_trace_path = example_dir / ".nlp2dsl" / "conversation.trace.json"
        exec_trace_path = example_dir / ".nlp2dsl" / "execution.trace.json"
        if conv_trace_path.is_file():
            try:
                last_response = response_from_e2e_trace(
                    json.loads(conv_trace_path.read_text(encoding="utf-8"))
                )
            except json.JSONDecodeError:
                pass
        if not last_response and exec_trace_path.is_file():
            try:
                last_response = response_from_e2e_trace(
                    json.loads(exec_trace_path.read_text(encoding="utf-8"))
                )
            except json.JSONDecodeError:
                pass

        pv_results = run_validations_from_raw(
            profile_validations,
            last_response,
            example_dir=example_dir,
        )
        pv_passed = all(r.get("passed") for r in pv_results)
        report["checks"].append({
            "id": "profile.validations",
            "status": "passed" if pv_passed else "failed",
            "summary": f"{sum(1 for r in pv_results if r.get('passed'))}/{len(pv_results)} profile checks",
            "validations": pv_results,
        })
        report["profile_validations"] = pv_results
        if not pv_passed:
            report["passed"] = False

    report["status"] = "passed" if report["passed"] else "failed"
    return report


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from _dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", nargs="*", help="Example ids (default: all with conversation or --all)")
    parser.add_argument("--all", action="store_true", help="Run all examples from profiles")
    parser.add_argument("--up", action="store_true", help="Start docker compose before tests")
    parser.add_argument("--down", action="store_true", help="Stop docker compose after tests")
    parser.add_argument("--build", action="store_true", help="Build images on up")
    parser.add_argument("--skip-main", action="store_true", help="Only run conversation scenarios")
    parser.add_argument("--llm", action="store_true", help="Also run LLM scenarios when OPENROUTER_API_KEY is set")
    parser.add_argument("--testql-results", action="store_true", help="Also run run-example-testql-results.py")
    parser.add_argument("--base-url", default="")
    args = parser.parse_args(argv)

    cfg = _load_profiles()
    defaults = cfg.get("defaults") or {}
    base_url = args.base_url or os.environ.get("NLP2DSL_URL") or defaults.get("nlp2dsl_url", "http://localhost:8010")
    timeout_s = float(defaults.get("health_timeout_s", 120))

    examples_cfg = cfg.get("examples") or {}
    if args.all:
        example_ids = sorted(examples_cfg.keys())
    elif args.examples:
        example_ids = list(args.examples)
    else:
        example_ids = [
            eid for eid, e in examples_cfg.items()
            if e.get("conversation") or e.get("execution_scenario")
        ]

    profiles = _collect_profiles(example_ids, cfg)
    if args.llm:
        profiles.add("llm")

    if args.up:
        docker_up(profiles, build=args.build)
        if not wait_platform(base_url, timeout_s):
            print(f"Platform not healthy at {base_url}", file=sys.stderr)
            if args.down:
                docker_down()
            return 1

    reports: list[dict[str, Any]] = []
    for eid in example_ids:
        entry = examples_cfg.get(eid)
        if not entry:
            print(f"Unknown example: {eid}", file=sys.stderr)
            continue
        print(f"\n==> Docker E2E: {eid}", flush=True)
        reports.append(process_example(eid, entry, base_url=base_url, skip_main=args.skip_main, run_llm=args.llm))

    if args.testql_results and RESULTS_SCRIPT.is_file():
        env = {**os.environ, "NLP2DSL_URL": base_url, "NLP2DSL_EXECUTE": "1"}
        subprocess.run([_py(), str(RESULTS_SCRIPT), *example_ids], cwd=ROOT, env=env, check=False)

    aggregate = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "docker_profiles": sorted(profiles),
        "examples": len(reports),
        "passed": sum(1 for r in reports if r.get("status") == "passed"),
        "failed": sum(1 for r in reports if r.get("status") == "failed"),
        "skipped": sum(1 for r in reports if r.get("status") == "skipped"),
        "results": reports,
    }
    out = ROOT / "examples" / "docker-e2e-results.json"
    out.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"\nWrote {out} — {aggregate['passed']} passed, "
        f"{aggregate['failed']} failed, {aggregate['skipped']} skipped "
        f"(of {aggregate['examples']} examples)"
    )

    if args.down:
        docker_down()

    return 1 if aggregate["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
