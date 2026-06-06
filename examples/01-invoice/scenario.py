"""Scenariusz: autonomiczne wysyłanie faktury — jedno zadanie, pełna pętla."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from nlp2dsl_sdk.autonomous_flow import AutonomousFlow
from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.example_bootstrap import ensure_doql_registry
from nlp2dsl_sdk.preview import ensure_services, execute_from_text, preview_text_examples

INVOICE_PROMPT = "Wyślij fakturę na 1500 PLN do klient@firma.pl"
INVOICE_TASK = "Wyślij fakturę"


def _example_dir() -> Path:
    return Path(__file__).resolve().parent


def _run_autonomous(client: NLP2DSLClient) -> dict[str, Any]:
    doql_path = ensure_doql_registry(_example_dir())
    print(f"📄 DOQL context: {doql_path.relative_to(_example_dir())}\n")

    flow = AutonomousFlow(client, reflect=True)
    result = flow.run_task(INVOICE_TASK)
    flow.save_artifacts(_example_dir())
    return result


def _attachment_validation(result: dict[str, Any]) -> dict[str, Any] | None:
    av = result.get("attachment_validation")
    if isinstance(av, dict):
        return av
    execution = result.get("execution") or {}
    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_result = step.get("result") or {}
        if isinstance(step_result, dict) and isinstance(step_result.get("attachment_validation"), dict):
            return step_result["attachment_validation"]
    return None


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie Faktury (autonomicznie) ===\n")

    if not ensure_services(client):
        return {}

    mode = os.environ.get("NLP2DSL_INVOICE_MODE", "conversation").strip().lower()

    if mode == "one-shot":
        preview_text_examples(client, "", [INVOICE_PROMPT], finalize_artifacts=False)
        result = execute_from_text(client, INVOICE_PROMPT, label="Wykonywanie z zapytania NLP")
    else:
        result = _run_autonomous(client)

    av = _attachment_validation(result)
    if result.get("status") == "executed" and av and av.get("status") != "ok":
        from nlp2dsl_sdk.attachment_validation import format_attachment_validation

        result["status"] = "artifact_invalid"
        result["message"] = format_attachment_validation(av) or "Załącznik nie przeszedł walidacji."

    if result.get("status") == "executed":
        execution = result.get("execution") or {}
        if execution.get("status") == "completed":
            steps = execution.get("steps") or [{}]
            step = steps[0] if steps else {}
            inv_id = (step.get("result") or {}).get("invoice_id", "?")
            print(f"\n🎉 Faktura wysłana! ID: {inv_id}")
        else:
            print(f"\n❌ Workflow: {execution.get('error', execution.get('status'))}")
    elif result.get("status") == "ready":
        print("\n⚠️  Workflow gotowy — auto_execute wyłączone (NLP2DSL_AUTO_EXECUTE=0).")
    else:
        print(f"\n❌ Nie udało się: {result.get('message', result.get('status'))}")
        reflection = result.get("reflection") or {}
        for q in reflection.get("context_queries") or []:
            print(f"   ❓ {q}")

    from nlp2dsl_sdk.artifacts import get_example_writer

    writer = get_example_writer()
    if writer:
        writer.record(INVOICE_TASK if mode != "one-shot" else INVOICE_PROMPT, result, mode="auto")
        writer.finalize(client)

    return result
