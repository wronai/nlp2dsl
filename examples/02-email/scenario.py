"""Scenariusz: wysyłanie e-maila — logika przykładu 02-email."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import (
    ensure_services,
    execute_from_text,
    preview_text_examples,
)

EMAIL_TEXT_EXAMPLES: tuple[str, ...] = (
    "Wyślij email do team@firma.pl z tematem Status projektu",
    "Napisz do manager@firma.pl: Projekt zakończony sukcesem",
    "Maila do klient@firma.pl z nową ofertą",
    "Przypomnij billing@firma.pl o nieopłaconej fakturze",
)

# Pełne zdanie z body — NLP → DSL → wykonanie (bez client.send_email)
EMAIL_EXECUTION_QUERY = (
    "Wyślij email do team@firma.pl z tematem Status dzienny. "
    "Treść: Wszystkie projekty przebiegają zgodnie z harmonogramem."
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie E-maila ===\n")

    if not ensure_services(client):
        return {}

    preview_text_examples(client, "", EMAIL_TEXT_EXAMPLES, finalize_artifacts=False)

    result = execute_from_text(client, EMAIL_EXECUTION_QUERY, label="Wykonywanie z zapytania NLP")

    if result.get("status") == "executed":
        execution = result.get("result", {})
        if execution.get("status") == "completed":
            print("\n🎉 E-mail wysłany pomyślnie!")
        else:
            print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")
    elif result.get("status") == "incomplete":
        print("\n⚠️  Brakuje pól — uzupełnij zapytanie lub użyj dialogu (examples/07)")
    else:
        print(f"\n❌ Błąd: {result.get('error', result.get('status'))}")

    from nlp2dsl_sdk.artifacts import get_example_writer

    writer = get_example_writer()
    if writer:
        writer.record(EMAIL_EXECUTION_QUERY, result, mode="auto")
        writer.finalize(client)

    return result
