"""Scenariusz: zaplanowane raporty — logika przykładu 04."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import (
    ensure_services,
    preview_text_examples,
    print_execution_result,
)

SCHEDULED_REPORT_SPECS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "daily_sales_report",
        "runner": lambda c: c.create_scheduled_report(
            name="daily_sales_report",
            report_type="sales",
            trigger="daily",
            schedule="09:00",
            email_to="team@firma.pl",
        ),
    },
    {
        "title": "weekly_hr_report",
        "runner": lambda c: c.create_scheduled_report(
            name="weekly_hr_report",
            report_type="hr",
            trigger="weekly",
            schedule="monday 08:00",
            email_to="hr@firma.pl",
            format_type="xlsx",
        ),
    },
    {
        "title": "monthly_finance_report",
        "runner": lambda c: c.create_scheduled_report(
            name="monthly_finance_report",
            report_type="finance",
            trigger="monthly",
            schedule="1st 07:00",
            email_to="cfo@firma.pl",
        ),
    },
    {
        "title": "business_hours_report",
        "runner": lambda c: c.create_scheduled_report(
            name="business_hours_report",
            report_type="sales",
            trigger="daily",
            schedule="09:00",
            email_to="manager@firma.pl",
            format_type="csv",
        ),
    },
)

SCHEDULED_REPORT_TEXT_EXAMPLES: tuple[str, ...] = (
    "Codziennie o 9:00 generuj raport sprzedaży",
    "Co poniedziałek raport HR do hr@firma.pl",
    "Pierwszego każdego miesiąca raport finansów",
    "Każdego dnia o 18:00 przygotuj raport sprzedaży dla zespołu",
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Zaplanowane Raporty ===\n")

    if not ensure_services(client):
        return {}

    print("📋 Tworzenie raportów z różnymi harmonogramami...\n")
    results: list[dict[str, Any]] = []
    for spec in SCHEDULED_REPORT_SPECS:
        print(f"\n📦 {spec['title']}")
        result = spec["runner"](client)
        results.append(result)
        print_execution_result(result)

    print("\n📝 Przykłady generowania z tekstu:")
    preview_text_examples(client, "", SCHEDULED_REPORT_TEXT_EXAMPLES)

    print("\n🎉 Wszystkie zaplanowane raporty zostały utworzone!")
    print("\n💡 Wskazówka: W systemie produkcyjnym te workflow byłyby uruchamiane")
    print("   automatycznie według zdefiniowanych harmonogramów.")

    return results[-1] if results else {}
