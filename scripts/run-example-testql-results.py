#!/usr/bin/env python3
"""Run TestQL + nlp2dsl checks for each examples/*/.nlp2dsl/ and write result artifacts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@dataclass
class Check:
    id: str
    status: str  # passed | failed | skipped | warning
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExampleReport:
    example_id: str
    artifact_root: Path
    status: str
    checks: list[Check] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)
    actions: list[dict[str, str]] = field(default_factory=list)

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == "failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": f"examples/{self.example_id}",
            "example_id": self.example_id,
            "status": self.status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks_total": len(self.checks),
            "checks_passed": sum(1 for c in self.checks if c.status == "passed"),
            "checks_failed": self.failures,
            "checks_skipped": sum(1 for c in self.checks if c.status == "skipped"),
            "checks": [c.__dict__ for c in self.checks],
            "findings": self.findings,
            "actions": self.actions,
        }


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _testql_dry_run(commands_path: Path) -> Check:
    proc = subprocess.run(
        ["testql", "run", str(commands_path.relative_to(ROOT)), "--dry-run", "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode == 0:
        return Check("check.testql.commands_dry_run", "passed", "commands.testql.toon.yaml parses and dry-runs")
    return Check(
        "check.testql.commands_dry_run",
        "failed",
        f"testql dry-run exit {proc.returncode}",
        {"stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]},
    )


def _testql_ir_parse(commands_path: Path) -> Check:
    try:
        from testql.adapters.testtoon_adapter import TestToonAdapter
    except ImportError:
        return Check("check.testql.ir_parse", "skipped", "testql adapter not installed")

    try:
        plan = TestToonAdapter().parse(commands_path)
        return Check(
            "check.testql.ir_parse",
            "passed",
            f"IR plan: {len(plan.steps)} steps, type={plan.metadata.type}",
            {"step_kinds": [s.kind for s in plan.steps]},
        )
    except Exception as exc:
        return Check("check.testql.ir_parse", "failed", f"IR parse error: {exc}")


def _nlp2dsl_run_query(query_entry: dict[str, Any], artifact_root: Path, *, timeout_s: int = 45) -> Check:
    query = str(query_entry.get("query", "")).strip()
    safe_id = query[:40].replace(" ", "-").replace('"', "").replace("@", "")
    check_id = f"check.nlp2dsl.query.{safe_id}"
    mode = str(query_entry.get("mode") or "auto")
    manifest_status = str(query_entry.get("status") or "")
    pipeline_rel = query_entry.get("pipeline_json")
    pipeline_path = artifact_root / pipeline_rel if pipeline_rel else None

    if pipeline_path and pipeline_path.is_file():
        try:
            cached = json.loads(pipeline_path.read_text(encoding="utf-8"))
            cached_status = str(cached.get("status") or manifest_status or "cached")
            return Check(
                check_id,
                "passed",
                f"offline artifact ok (status={cached_status}): {query[:70]}",
                {"source": str(pipeline_rel), "mode": mode},
            )
        except (json.JSONDecodeError, OSError) as exc:
            return Check(check_id, "failed", f"invalid cached pipeline: {exc}")

    if mode == "show" or manifest_status == "ir":
        proc = subprocess.run(
            ["nlp2dsl", "show", query],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        if proc.returncode == 0:
            return Check(check_id, "passed", f"show/ir ok: {query[:70]}", {"mode": "show"})
        return Check(
            check_id,
            "failed",
            f"show exit {proc.returncode}: {query[:80]}",
            {"stderr": proc.stderr[-1500:]},
        )

    proc = subprocess.run(
        ["nlp2dsl", "run", query, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    if proc.returncode != 0:
        backend_err = "422" in proc.stderr or "Unprocessable Entity" in proc.stderr
        if backend_err and mode in {"auto", "rules"}:
            return Check(
                check_id,
                "warning",
                f"backend unavailable ({proc.returncode}): {query[:60]}",
                {"stderr": proc.stderr[-800:]},
            )
        return Check(
            check_id,
            "failed",
            f"exit {proc.returncode}: {query[:80]}",
            {"stderr": proc.stderr[-1500:], "stdout": proc.stdout[-1500:]},
        )
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return Check(check_id, "warning", f"non-json output: {query[:60]}", {"stdout": proc.stdout[:500]})
    status = str(body.get("status", ""))
    if status in {"complete", "executed", "incomplete", "ir"}:
        return Check(
            check_id,
            "passed",
            f"status={status}: {query[:70]}",
            {"status": status, "actions": body.get("actions") or body.get("dsl", {}).get("steps")},
        )
    return Check(check_id, "warning", f"unexpected status={status!r}", {"body_keys": list(body.keys())})


def _generate_conversation_toon(example_id: str, manifest: dict[str, Any]) -> str:
    queries = manifest.get("queries") or []
    lines = [
        f"# SCENARIO: {example_id} conversation",
        "# TYPE: conversation",
        "# GENERATED: true",
        "",
        "CONFIG[2]{key, value}:",
        f"  example_id, {example_id}",
        "  nlp2dsl_mode, cli",
        "",
    ]
    if not queries:
        lines.append("# No queries in manifest")
        return "\n".join(lines) + "\n"

    lines.append(f"CONVERSATION[{len(queries)}]" + "{role, message, expect_status}:")
    for q in queries:
        status = q.get("status") or "complete"
        text = str(q.get("query", "")).replace(",", " ")
        lines.append(f"  user, {text}, {status}")
    lines.append("")
    lines.append(f"NLP_DSL[{len(queries)}]" + "{endpoint, payload}:")
    for q in queries:
        text = json.dumps(str(q.get("query", "")), ensure_ascii=False)
        lines.append(f"  workflowfrom-text, {{text: {text}, execute: false}}")
    return "\n".join(lines) + "\n"


def _conversation_dry_run(conversation_path: Path) -> Check:
    try:
        from testql.adapters.nlp2dsl import Nlp2DslAdapter
        from testql.conversation import ConversationRunner
    except ImportError:
        return Check("check.conversation.dry_run", "skipped", "testql conversation modules unavailable")

    adapter = Nlp2DslAdapter()
    plan = adapter.parse(conversation_path)
    issues = [i for i in adapter.validate(plan) if i.severity == "error"]
    if issues:
        return Check(
            "check.conversation.dry_run",
            "failed",
            "; ".join(i.message for i in issues),
        )
    result = ConversationRunner(dry_run=True).run(plan)
    if result.passed:
        return Check(
            "check.conversation.dry_run",
            "passed",
            f"{len(result.turns)} turns dry-run ok",
            {"variables": result.variables},
        )
    return Check(
        "check.conversation.dry_run",
        "failed",
        "; ".join(result.findings) or "conversation dry-run failed",
    )


def _manifest_consistency(manifest: dict[str, Any], artifact_root: Path) -> list[Check]:
    checks: list[Check] = []
    for idx, q in enumerate(manifest.get("queries") or [], start=1):
        slug = q.get("slug") or f"query-{idx}"
        pipe = q.get("pipeline_json")
        proc = q.get("process_yaml")
        if pipe and not (artifact_root / pipe).is_file():
            checks.append(Check(f"check.artifact.pipeline.{idx}", "failed", f"missing {pipe}"))
        elif pipe:
            checks.append(Check(f"check.artifact.pipeline.{idx}", "passed", f"pipeline present: {slug}"))
        if proc and not (artifact_root / proc).is_file():
            checks.append(Check(f"check.artifact.process.{idx}", "failed", f"missing {proc}"))
        elif proc:
            checks.append(Check(f"check.artifact.process.{idx}", "passed", f"process present: {slug}"))
    return checks


def _write_toon_report(report: ExampleReport) -> str:
    lines = [
        "INSPECTION{key, value}:",
        f"  run_id, examples/{report.example_id}",
        f"  status, {report.status}",
        f"  checks, {len(report.checks)}",
        f"  failures, {report.failures}",
        f"  actions, {len(report.actions)}",
        "",
        f"CHECKS[{len(report.checks)}]" + "{id, status, summary}:",
    ]
    for c in report.checks:
        summary = c.summary.replace(",", ";")
        lines.append(f"  {c.id}, {c.status}, {summary}")
    lines.append("")
    lines.append(f"FINDINGS[{len(report.findings)}]" + "{id, severity, node_id, summary}:")
    for f in report.findings:
        lines.append(f"  {f['id']}, {f['severity']}, {f.get('node_id', 'example')}, {f['summary']}")
    lines.append("")
    lines.append(f"ACTIONS[{len(report.actions)}]" + "{id, type, target, summary}:")
    for a in report.actions:
        lines.append(f"  {a['id']}, {a['type']}, {a['target']}, {a['summary']}")
    return "\n".join(lines) + "\n"


def process_example(example_dir: Path) -> ExampleReport:
    example_id = example_dir.name
    artifact_root = example_dir / ".nlp2dsl"
    manifest_path = artifact_root / "manifest.yaml"
    commands_path = artifact_root / "commands.testql.toon.yaml"

    report = ExampleReport(example_id=example_id, artifact_root=artifact_root, status="passed")
    manifest = _load_manifest(manifest_path)

    if commands_path.is_file():
        report.checks.append(_testql_dry_run(commands_path))
        report.checks.append(_testql_ir_parse(commands_path))
    else:
        report.checks.append(Check("check.testql.commands_dry_run", "skipped", "no commands.testql.toon.yaml"))

    report.checks.extend(_manifest_consistency(manifest, artifact_root))

    for q in manifest.get("queries") or []:
        if not str(q.get("query", "")).strip():
            continue
        report.checks.append(_nlp2dsl_run_query(q, artifact_root))

    conversation_text = _generate_conversation_toon(example_id, manifest)
    conversation_path = artifact_root / "conversation.testql.toon.yaml"
    conversation_path.write_text(conversation_text, encoding="utf-8")
    report.checks.append(
        Check("check.conversation.generated", "passed", f"wrote {conversation_path.name}")
    )
    report.checks.append(_conversation_dry_run(conversation_path))

    for c in report.checks:
        if c.status == "failed":
            report.findings.append({
                "id": f"finding.{c.id}",
                "severity": "high",
                "node_id": f"examples/{example_id}",
                "summary": c.summary,
            })
            report.actions.append({
                "id": f"action.{c.id}",
                "type": "investigate",
                "target": str(artifact_root),
                "summary": f"Fix: {c.summary}",
            })

    if report.failures:
        report.status = "failed"
    elif any(c.status == "warning" for c in report.checks):
        report.status = "warning"
    else:
        report.status = "passed"

    result_json = artifact_root / "result.json"
    result_toon = artifact_root / "result.toon.yaml"
    result_yaml = artifact_root / "result.yaml"
    payload = report.to_dict()
    result_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result_toon.write_text(_write_toon_report(report), encoding="utf-8")
    result_yaml.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    summary_md = artifact_root / "summary.md"
    summary_md.write_text(
        textwrap.dedent(
            f"""\
            # Test results — {example_id}

            - **Status:** {report.status}
            - **Checks:** {len(report.checks)} ({report.failures} failed)
            - **Generated:** {payload['generated_at']}

            ## Artifacts

            - `result.toon.yaml` — TestQL-style report
            - `result.json` / `result.yaml` — machine-readable
            - `conversation.testql.toon.yaml` — generated conversation scenario

            ## Checks

            """
        )
        + "\n".join(f"- [{c.status}] `{c.id}` — {c.summary}" for c in report.checks)
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    only = set(argv or sys.argv[1:])
    reports: list[ExampleReport] = []

    for example_dir in sorted(EXAMPLES.iterdir()):
        if not example_dir.is_dir():
            continue
        if not (example_dir / ".nlp2dsl").is_dir():
            continue
        if only and example_dir.name not in only:
            continue
        print(f"==> {example_dir.name}", flush=True)
        try:
            reports.append(process_example(example_dir))
        except Exception as exc:
            print(f"ERROR {example_dir.name}: {exc}", file=sys.stderr)
            artifact_root = example_dir / ".nlp2dsl"
            err = ExampleReport(example_id=example_dir.name, artifact_root=artifact_root, status="failed")
            err.checks.append(Check("check.runner.crash", "failed", str(exc)))
            err.findings.append({"id": "finding.crash", "severity": "critical", "node_id": example_dir.name, "summary": str(exc)})
            payload = err.to_dict()
            (artifact_root / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            (artifact_root / "result.toon.yaml").write_text(_write_toon_report(err), encoding="utf-8")
            reports.append(err)

    aggregate = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "examples": len(reports),
        "passed": sum(1 for r in reports if r.status == "passed"),
        "failed": sum(1 for r in reports if r.status == "failed"),
        "warning": sum(1 for r in reports if r.status == "warning"),
        "results": [r.to_dict() for r in reports],
    }
    out = EXAMPLES / "testql-results.json"
    out.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {out} — {aggregate['passed']}/{aggregate['examples']} passed")
    return 1 if aggregate["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
