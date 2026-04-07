#!/usr/bin/env python3
"""
Przykład wysyłania faktury przez API NLP2DSL.
"""

import json
import sys
from typing import Any

import requests

BASE_URL = "http://localhost:8010"


def send_invoice(amount: float, to: str, currency: str = "PLN") -> dict[str, Any]:
    """Wyślij fakturę przez API."""

    # Metoda 1: Bezpośrednie wywołanie DSL
    print("📤 Wysyłanie faktury...")

    payload = {
        "name": "invoice_example",
        "steps": [
            {
                "action": "send_invoice",
                "config": {
                    "amount": amount,
                    "to": to,
                    "currency": currency
                }
            }
        ]
    }

    response = requests.post(f"{BASE_URL}/workflow/run", json=payload)
    response.raise_for_status()

    return response.json()


def generate_invoice_from_text(text: str) -> dict[str, Any]:
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

    print("=== Przykład: Wysyłanie Faktury ===\n")

    # Sprawdź połączenie z API
    try:
        requests.get(f"{BASE_URL}/docs")
    except requests.exceptions.ConnectionError:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        sys.exit(1)

    # Przykład 1: Generowanie z tekstu
    text = "Wyślij fakturę na 1500 PLN do klient@firma.pl"
    result = generate_invoice_from_text(text)

    print("✅ Wygenerowany DSL:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()

    # Przykład 2: Bezpośrednie wywołanie
    print("📋 Wykonywanie workflow...")
    execution = send_invoice(1500, "klient@firma.pl", "PLN")

    print("✅ Wynik wykonania:")
    print(json.dumps(execution, indent=2, ensure_ascii=False))

    # Sprawdź wynik
    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            invoice_id = step["result"]["invoice_id"]
            print(f"\n🎉 Faktura wysłana! ID: {invoice_id}")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")


if __name__ == "__main__":
    main()
