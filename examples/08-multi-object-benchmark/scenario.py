"""Benchmark 20 zapytań — skuteczność NLP→DSL (rules / auto / llm)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from benchmark_queries import BENCHMARK_QUERIES, BenchmarkQuery
from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.artifacts import get_example_writer
from nlp2dsl_sdk.preview import ensure_services, print_workflow_preview

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _extract_actions(result: dict[str, Any]) -> list[str]:
    dsl = result.get("dsl") or result.get("partial_workflow") or result.get("workflow")
    if not dsl:
        return []
    return [s.get("action", "") for s in dsl.get("steps", [])]


def _evaluate(query: BenchmarkQuery, result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status", "error")
    actions = _extract_actions(result)
    intent_ok = any(query.expected_intent in a for a in actions) or (
        query.expected_intent in str(result.get("dsl", result.get("partial_workflow", "")))
    )
    actions_ok = all(any(exp in a for a in actions) for exp in query.expected_actions)
    complete = status in ("complete", "executed")
    return {
        "status": status,
        "actions": actions,
        "intent_ok": intent_ok,
        "actions_ok": actions_ok,
        "complete": complete,
        "missing": result.get("missing_fields", []),
        "pass": complete and actions_ok,
    }


def run_benchmark(
    client: NLP2DSLClient,
    *,
    mode: str = "auto",
    execute: bool = False,
    verbose: bool = True,
    artifact_writer: Any | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    for query in BENCHMARK_QUERIES:
        if verbose:
            print(f"\n{'─' * 60}")
            print(f"[{query.id}] {query.category}: {query.text[:70]}…")
            print(f"    mode={mode}  expected={query.expected_actions}")

        try:
            result = client.workflow_from_text(query.text, execute=execute, mode=mode)
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}

        eval_row = _evaluate(query, result)
        row = {
            "id": query.id,
            "text": query.text,
            "category": query.category,
            "mode": mode,
            **eval_row,
        }
        rows.append(row)
        if artifact_writer:
            artifact_writer.record(query.text, result, mode=mode)

        if verbose:
            icon = "✅" if row["pass"] else ("⚠️" if row["status"] == "incomplete" else "❌")
            print(f"    {icon} status={row['status']} actions={row['actions']}")
            if row.get("missing"):
                print(f"       missing: {row['missing']}")
            if row["status"] not in ("complete", "executed", "incomplete"):
                print(f"       error: {result.get('error', result)}")

    elapsed = time.perf_counter() - t0
    passed = sum(1 for r in rows if r["pass"])
    complete = sum(1 for r in rows if r["complete"])
    intent_ok = sum(1 for r in rows if r["intent_ok"])

    summary = {
        "mode": mode,
        "total": len(rows),
        "passed": passed,
        "complete": complete,
        "intent_ok": intent_ok,
        "pass_rate": round(100 * passed / len(rows), 1),
        "complete_rate": round(100 * complete / len(rows), 1),
        "elapsed_s": round(elapsed, 1),
        "rows": rows,
    }
    return summary


def run(
    client: Optional[NLP2DSLClient] = None,
    *,
    modes: tuple[str, ...] = ("rules", "auto"),
) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Benchmark: 20 zapytań multi-object ===\n")

    if not ensure_services(client):
        return {}

    writer = get_example_writer()
    all_summaries: dict[str, Any] = {}
    for mode in modes:
        print(f"\n{'=' * 60}\n  TRYB: {mode}\n{'=' * 60}")
        summary = run_benchmark(client, mode=mode, verbose=True, artifact_writer=writer)
        all_summaries[mode] = summary
        print(
            f"\n📊 {mode}: pass={summary['passed']}/{summary['total']} "
            f"({summary['pass_rate']}%)  complete={summary['complete']}  "
            f"czas={summary['elapsed_s']}s"
        )

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"benchmark_{int(time.time())}.json"
    out.write_text(json.dumps(all_summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Wyniki zapisane: {out}")

    if writer:
        writer.finalize(client)
        print(f"📁 Artefakty: {writer.artifact_root}")

    return all_summaries
