"""Scenariusz: wysyłanie faktury — logika przykładu 01-invoice."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, preview_text_examples, print_execution_result

INVOICE_PROMPT = "Wyślij fakturę na 1500 PLN do klient@firma.pl"
AMOUNT = 1500.0


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie Faktury ===\n")

    if not ensure_services(client):
        return {}

    preview_text_examples(client, "", [INVOICE_PROMPT], finalize_artifacts=False)

    print("📋 Wykonywanie workflow...")
    execution = client.send_invoice(AMOUNT, "klient@firma.pl", "PLN")
    print_execution_result(execution)

    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            print(f"\n🎉 Faktura wysłana! ID: {step['result']['invoice_id']}")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    from nlp2dsl_sdk.artifacts import get_example_writer

    writer = get_example_writer()
    if writer:
        writer.record(
            INVOICE_PROMPT,
            {"status": "executed", "dsl": {"name": "invoice_example", "steps": [{"action": "send_invoice"}]}, "result": execution},
            mode="auto",
        )
        writer.finalize(client)

    return execution
