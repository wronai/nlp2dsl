"""Scenariusz: raport + powiadomienia — logika przykładu 03."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, preview_text_examples, print_execution_result

REPORT_TEXT_EXAMPLES: tuple[str, ...] = (
    "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl",
    "Generuj raport HR i powiadom na #hr",
    "Miesięczny raport finansów do CFO i teamu",
    "Raport kwartalny sprzedaży w CSV i wyślij go do #sales",
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Raport i Powiadomienia ===\n")

    if not ensure_services(client):
        return {}

    preview_text_examples(client, "", REPORT_TEXT_EXAMPLES)

    print("\n📋 Wykonywanie workflow z wieloma krokami...")
    execution = client.generate_report_and_notify(
        report_type="sales",
        format_type="pdf",
        email_to="manager@firma.pl",
        slack_channel="#sales",
        trigger="weekly",
    )
    print_execution_result(execution)

    if execution.get("status") == "completed":
        print("\n🎉 Workflow wykonany pomyślnie!")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    return execution
