#!/usr/bin/env python3
"""
Przykład wysyłania e-maila przez API NLP2DSL.
"""

import json
import sys
from typing import Any

import requests

BASE_URL = "http://localhost:8010"


def send_email(to: str, subject: str = None, body: str = None) -> dict[str, Any]:
    """Wyślij e-mail przez API."""

    print(f"📧 Wysyłanie e-maila do: {to}")

    payload = {
        "name": "email_example",
        "steps": [
            {
                "action": "send_email",
                "config": {
                    "to": to,
                    "subject": subject or "Automatyczna wiadomość",
                    "body": body or "Wiadomość wygenerowana automatycznie."
                }
            }
        ]
    }

    response = requests.post(f"{BASE_URL}/workflow/run", json=payload)
    response.raise_for_status()

    return response.json()


def generate_email_from_text(text: str) -> dict[str, Any]:
    """Generuj DSL z języka naturalnego."""

    print(f"🧠 Analiza tekstu: '{text}'")

    response = requests.post(
        f"{BASE_URL}/workflow/from-text",
        json={"text": text}
    )
    response.raise_for_status()

    return response.json()


def main():
    """Główna funkcja przykładu."""

    print("=== Przykład: Wysyłanie E-maila ===\n")

    # Sprawdź połączenie
    try:
        requests.get(f"{BASE_URL}/docs")
    except requests.exceptions.ConnectionError:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        sys.exit(1)

    # Przykład 1: Generowanie z tekstu
    examples = [
        "Wyślij email do team@firma.pl z tematem Status projektu",
        "Napisz do manager@firma.pl: Projekt zakończony sukcesem",
        "Maila do klient@firma.pl z nową ofertą"
    ]

    for text in examples:
        print(f"\n📝 Przykład: {text}")
        result = generate_email_from_text(text)

        if result.get("status") == "complete":
            print("✅ Wygenerowany DSL:")
            print(json.dumps(result["dsl"], indent=2, ensure_ascii=False))

    # Przykład 2: Bezpośrednie wywołanie
    print("\n📋 Wykonywanie workflow...")
    execution = send_email(
        to="team@firma.pl",
        subject="Status dzienny projektów",
        body="Wszystkie projekty przebiegają zgodnie z harmonogramem."
    )

    print("✅ Wynik wykonania:")
    print(json.dumps(execution, indent=2, ensure_ascii=False))

    # Sprawdź wynik
    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            print(f"\n🎉 E-mail wysłany pomyślnie!")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")


if __name__ == "__main__":
    main()
