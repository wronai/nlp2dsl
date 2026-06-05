"""Scenariusz: wysyłanie e-maila — logika przykładu 02-email."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, preview_text_examples, print_execution_result

EMAIL_TEXT_EXAMPLES: tuple[str, ...] = (
    "Wyślij email do team@firma.pl z tematem Status projektu",
    "Napisz do manager@firma.pl: Projekt zakończony sukcesem",
    "Maila do klient@firma.pl z nową ofertą",
    "Przypomnij billing@firma.pl o nieopłaconej fakturze",
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie E-maila ===\n")

    if not ensure_services(client):
        return {}

    preview_text_examples(client, "", EMAIL_TEXT_EXAMPLES)

    print("\n📋 Wykonywanie workflow...")
    execution = client.send_email(
        to="team@firma.pl",
        subject="Status dzienny projektów",
        body="Wszystkie projekty przebiegają zgodnie z harmonogramem.",
    )
    print_execution_result(execution)

    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            print("\n🎉 E-mail wysłany pomyślnie!")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    return execution
