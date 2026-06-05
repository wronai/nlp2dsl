"""Scenariusz: autonomiczny stack faktur — multi-turn, walidacja, compose + cron."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services
from nlp2dsl_sdk.stack_flow import AutonomousStackFlow, DEFAULT_STACK_TURNS


def _example_dir() -> Path:
    return Path(__file__).resolve().parent


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład 13: Autonomiczny stack faktur (compose + cron) ===\n")

    if not ensure_services(client):
        return {"ok": False}

    mode = os.environ.get("NLP2DSL_STACK_MODE", "full").strip().lower()
    attachment = mode != "no-attachment"

    flow = AutonomousStackFlow(
        client,
        example_dir=_example_dir(),
        reflect=True,
        attachment=attachment,
    )

    turns = DEFAULT_STACK_TURNS
    if mode == "invoice-only":
        turns = tuple(t for t in turns if t[1] in ("bootstrap", "invoice_autonomous"))

    result = flow.run_phases(turns)

    if result.ok:
        print("\n🎉 Stack gotowy — registry, wykonanie i artefakty compose wygenerowane.")
        last_exec = next(
            (p for p in reversed(result.phases) if p.status == "executed"),
            None,
        )
        if last_exec and last_exec.response:
            execution = last_exec.response.get("execution") or {}
            steps = execution.get("steps") or [{}]
            inv_id = (steps[0].get("result") or {}).get("invoice_id")
            if inv_id:
                print(f"   Ostatnia faktura: {inv_id}")
    else:
        print("\n⚠️  Część faz nie powiodła się — sprawdź .nlp2dsl/runs/ i reflection.")

    from nlp2dsl_sdk.artifacts import get_example_writer

    writer = get_example_writer()
    if writer:
        writer.record("autonomous-invoice-stack", {"phases": [p.name for p in result.phases]}, mode="stack")
        writer.finalize(client)

    return {
        "ok": result.ok,
        "registry": str(result.registry_path) if result.registry_path else None,
        "compose": str(result.compose.stack_compose) if result.compose else None,
        "up_command": result.compose.up_command if result.compose else None,
    }
