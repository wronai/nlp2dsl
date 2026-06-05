"""Smoke test wykonania — 5 różnych obiektów end-to-end."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, print_execution_result

EXECUTION_CASES: tuple[tuple[str, str], ...] = (
    ("invoice", "Wyślij fakturę na 500 PLN do test@firma.pl"),
    ("slack", "Powiadom #ops: backup zakończony"),
    ("report", "Generuj raport sprzedaży PDF"),
    ("crm", "Zaktualizuj lead w CRM firma TestCo status new"),
    ("composite", "Faktura 200 PLN do a@b.pl i powiadom #billing"),
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Smoke test wykonania (execute=true) ===\n")

    if not ensure_services(client):
        return {}

    results: dict[str, Any] = {}
    for name, text in EXECUTION_CASES:
        print(f"\n▶ {name}: {text}")
        preview = client.workflow_from_text(text, execute=True, mode="auto")
        results[name] = preview
        if preview.get("status") == "executed":
            print_execution_result(preview.get("result", {}))
            if name == "slack":
                steps = preview.get("result", {}).get("steps", [])
                if steps:
                    msg = steps[0].get("result", {}).get("message", "")
                    print(f"   message: {msg}")
            print("✅ executed")
        else:
            print(f"⚠️  status={preview.get('status')} missing={preview.get('missing_fields')}")

    ok = sum(1 for r in results.values() if r.get("status") == "executed")
    print(f"\n📊 Wykonano: {ok}/{len(EXECUTION_CASES)}")
    return results
