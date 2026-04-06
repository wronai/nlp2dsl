#!/usr/bin/env python3
"""
Przykład generowania raportu i wysyłania powiadomień do wielu kanałów.
"""

import json
import requests
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8010"


def generate_report_and_notify(
    report_type: str,
    format_type: str = "pdf",
    email_to: str = None,
    slack_channel: str = None,
    trigger: str = "manual"
) -> Dict[str, Any]:
    """Generuj raport i wyślij powiadomienia."""
    
    print(f"📊 Generowanie raportu: {report_type} ({format_type})")
    
    steps = [
        {
            "action": "generate_report",
            "config": {
                "report_type": report_type,
                "format": format_type
            }
        }
    ]
    
    # Dodaj e-mail jeśli podany
    if email_to:
        print(f"📧 Dodawanie powiadomienia email do: {email_to}")
        steps.append({
            "action": "send_email",
            "config": {
                "to": email_to,
                "subject": f"Raport {report_type}",
                "body": f"Automatycznie wygenerowany raport {report_type} w formacie {format_type}."
            }
        })
    
    # Dodaj Slack jeśli podany
    if slack_channel:
        print(f"💬 Dodawanie powiadomienia Slack na: {slack_channel}")
        steps.append({
            "action": "notify_slack",
            "config": {
                "channel": slack_channel,
                "message": f"📊 Nowy raport {report_type} jest dostępny!"
            }
        })
    
    payload = {
        "name": f"{report_type}_report_workflow",
        "trigger": trigger,
        "steps": steps
    }
    
    response = requests.post(f"{BASE_URL}/workflow/run", json=payload)
    response.raise_for_status()
    
    return response.json()


def generate_composite_from_text(text: str) -> Dict[str, Any]:
    """Generuj DSL z tekstu z wieloma akcjami."""
    
    print(f"🧠 Analiza composite intent: '{text}'")
    
    response = requests.post(
        f"{BASE_URL}/workflow/from-text",
        json={"text": text}
    )
    response.raise_for_status()
    
    return response.json()


def main():
    """Główna funkcja przykładu."""
    
    print("=== Przykład: Raport i Powiadomienia ===\n")
    
    # Sprawdź połączenie
    try:
        requests.get(f"{BASE_URL}/docs")
    except requests.exceptions.ConnectionError:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        sys.exit(1)
    
    # Przykład 1: Composite intent z tekstu
    composite_examples = [
        "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl",
        "Generuj raport HR i powiadom na #hr",
        "Miesięczny raport finansów do CFO i teamu"
    ]
    
    for text in composite_examples:
        print(f"\n📝 Przykład: {text}")
        result = generate_composite_from_text(text)
        
        if result.get("status") == "complete":
            print("✅ Wygenerowany DSL:")
            print(json.dumps(result["dsl"], indent=2, ensure_ascii=False))
            print(f"   Liczba kroków: {len(result['dsl']['steps'])}")
    
    # Przykład 2: Bezpośrednie wywołanie z wieloma kanałami
    print("\n📋 Wykonywanie workflow z wieloma krokami...")
    execution = generate_report_and_notify(
        report_type="sales",
        format_type="pdf",
        email_to="manager@firma.pl",
        slack_channel="#sales",
        trigger="weekly"
    )
    
    print("\n✅ Wynik wykonania:")
    print(json.dumps(execution, indent=2, ensure_ascii=False))
    
    # Analiza wyników
    if execution.get("status") == "completed":
        print("\n🎉 Workflow wykonany pomyślnie!")
        for i, step in enumerate(execution["steps"], 1):
            status = "✅" if step.get("status") == "completed" else "❌"
            print(f"   Krok {i} ({step['action']}): {status}")
            if step.get("error"):
                print(f"      Błąd: {step['error']}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")


if __name__ == "__main__":
    main()
