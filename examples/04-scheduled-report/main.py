#!/usr/bin/env python3
"""
Przykład tworzenia zaplanowanych raportów z różnymi harmonogramami.
"""

import json
import sys
from datetime import UTC, datetime
from typing import Any

import requests

BASE_URL = "http://localhost:8010"


def create_scheduled_report(
    name: str,
    report_type: str,
    trigger: str,
    schedule: str | None = None,
    email_to: str = None,
    format_type: str = "pdf"
) -> dict[str, Any]:
    """Utwórz zaplanowany raport."""

    print(f"📅 Tworzenie raportu: {name}")
    print(f"   Typ: {report_type}, Trigger: {trigger}")
    if schedule:
        print(f"   Harmonogram: {schedule}")

    # Krok 1: Generuj raport
    steps = [
        {
            "action": "generate_report",
            "config": {
                "report_type": report_type,
                "format": format_type
            }
        }
    ]

    # Krok 2: Wyślij email jeśli podany
    if email_to:
        steps.append({
            "action": "send_email",
            "config": {
                "to": email_to,
                "subject": f"Automatyczny raport {report_type}",
                "body": f"Raport {report_type} wygenerowany automatycznie dnia {datetime.now(UTC).strftime('%Y-%m-%d')}."
            }
        })

    payload = {
        "name": name,
        "trigger": trigger
    }

    if schedule:
        payload["schedule"] = schedule

    payload["steps"] = steps

    response = requests.post(f"{BASE_URL}/workflow/run", json=payload)
    response.raise_for_status()

    return response.json()


def create_scheduled_from_text(text: str) -> dict[str, Any]:
    """Utwórz raport z tekstu zawierającego trigger."""

    print(f"🧠 Analiza tekstu z harmonogramiem: '{text}'")

    response = requests.post(
        f"{BASE_URL}/workflow/from-text",
        json={"text": text}
    )
    response.raise_for_status()

    return response.json()


def main() -> None:
    """Główna funkcja przykładu."""

    print("=== Przykład: Zaplanowane Raporty ===\n")

    # Sprawdź połączenie
    try:
        requests.get(f"{BASE_URL}/docs")
    except requests.exceptions.ConnectionError:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        sys.exit(1)

    # Przykład 1: Różne typy harmonogramów
    print("📋 Tworzenie raportów z różnymi harmonogramami...\n")

    reports = [
        {
            "name": "daily_sales_report",
            "report_type": "sales",
            "trigger": "daily",
            "schedule": "09:00",
            "email_to": "team@firma.pl"
        },
        {
            "name": "weekly_hr_report",
            "report_type": "hr",
            "trigger": "weekly",
            "schedule": "monday 08:00",
            "email_to": "hr@firma.pl",
            "format_type": "xlsx"
        },
        {
            "name": "monthly_finance_report",
            "report_type": "finance",
            "trigger": "monthly",
            "schedule": "1st 07:00",
            "email_to": "cfo@firma.pl"
        }
    ]

    for report in reports:
        result = create_scheduled_report(**report)
        print(f"✅ Status: {result.get('status')}")
        print(f"   Workflow ID: {result.get('workflow_id', 'N/A')}")
        print()

    # Przykład 2: Generowanie z tekstu
    print("\n📝 Przykłady generowania z tekstu:")

    text_examples = [
        "Codziennie o 9:00 generuj raport sprzedaży",
        "Co poniedziałek raport HR do hr@firma.pl",
        "Pierwszego każdego miesiąca raport finansów"
    ]

    for text in text_examples:
        print(f"\n🧠 '{text}'")
        result = create_scheduled_from_text(text)

        if result.get("status") == "complete":
            dsl = result["dsl"]
            print(f"✅ Trigger: {dsl.get('trigger', 'manual')}")
            print(f"   Kroki: {len(dsl.get('steps', []))}")

    # Przykład 3: Raport z zaawansowanym harmonogramem
    print("\n📋 Tworzenie raportu zaawansowanego...")
    advanced = create_scheduled_report(
        name="business_hours_report",
        report_type="sales",
        trigger="daily",
        schedule="09:00",
        email_to="manager@firma.pl",
        format_type="csv"
    )

    print("\n✅ Wynik wykonania:")
    print(json.dumps(advanced, indent=2, ensure_ascii=False))

    print("\n🎉 Wszystkie zaplanowane raporty zostały utworzone!")
    print("\n💡 Wskazówka: W systemie produkcyjnym te workflow byłyby uruchamiane")
    print("   automatycznie według zdefiniowanych harmonogramów.")


if __name__ == "__main__":
    main()
