#!/usr/bin/env python3
"""
Przykład pełnego konwersacyjnego flow z platformą NLP2DSL.
"""

import sys
from typing import Any

import requests

BASE_URL = "http://localhost:8010"


class ConversationFlow:
    """Klasa do obsługi konwersacyjnego flow."""

    def __init__(self):
        self.conversation_id: str | None = None
        self.history: list = []

    def start(self, text: str) -> dict[str, Any]:
        """Rozpocznij nową konwersację."""
        print(f"👤 Użytkownik: {text}")

        response = requests.post(
            f"{BASE_URL}/workflow/chat/start",
            json={"text": text}
        )
        response.raise_for_status()

        data = response.json()
        self.conversation_id = data["conversation_id"]
        self.history.append({"role": "user", "text": text})

        self._handle_response(data)
        return data

    def send_message(self, text: str) -> dict[str, Any]:
        """Wyślij wiadomość w istniejącej konwersacji."""
        print(f"👤 Użytkownik: {text}")

        if not self.conversation_id:
            raise ValueError("Brak ID konwersacji. Najpierw wywołaj start().")

        response = requests.post(
            f"{BASE_URL}/workflow/chat/message",
            json={"conversation_id": self.conversation_id, "text": text}
        )
        response.raise_for_status()

        data = response.json()
        self.history.append({"role": "user", "text": text})
        self._handle_response(data)
        return data

    def _handle_response(self, data: dict[str, Any]):
        """Obsłuż odpowiedź z API."""
        status = data.get("status")
        message = data.get("message", "")

        if status == "in_progress":
            print(f"🤖 System: {message}")

            # Pokaż formularz jeśli dostępny
            if data.get("form"):
                form = data["form"]
                print(f"\n📋 Formularz: {form.get('description', '')}")
                for field in form["fields"]:
                    required = "(wymagane)" if field["required"] else "(opcjonalne)"
                    print(f"   • {field['label']}: {field['type']} {required}")
                    if field.get("options"):
                        print(f"     Opcje: {', '.join(field['options'])}")
                print()

            # Pokaż brakujące pola
            if data.get("missing"):
                print(f"❗ Brakuje: {', '.join(data['missing'])}\n")

        elif status == "ready":
            print(f"🤖 System: {message}")
            if data.get("dsl"):
                dsl = data["dsl"]
                print(f"📝 Workflow: {dsl['name']} ({len(dsl['steps'])} kroków)")
                for i, step in enumerate(dsl["steps"], 1):
                    config = step["config"]
                    print(f"   Krok {i}: {step['action']}")
                    for key, value in config.items():
                        print(f"      {key}: {value}")
                print()

        elif status == "completed":
            print(f"🤖 System: {message}")
            if data.get("execution"):
                exec_data = data["execution"]
                print("✅ Wynik wykonania:")
                for step in exec_data.get("steps", []):
                    if step.get("status") == "completed":
                        result = step.get("result", {})
                        print(f"   • {step['action']}: {result}")
                print()

        elif status == "error":
            print(f"❌ Błąd: {message}\n")

        self.history.append({"role": "assistant", "text": message})

    def run_demo(self):
        """Uruchom demonstracyjny flow."""
        print("=== Demonstracja Konwersacyjnego Flow ===\n")

        # Sprawdź połączenie
        try:
            requests.get(f"{BASE_URL}/docs")
        except requests.exceptions.ConnectionError:
            print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
            sys.exit(1)

        # Krok 1: Inicjalizacja
        print("🚀 Krok 1: Inicjalizacja konwersacji")
        self.start("Chcę wysłać fakturę")

        # Krok 2: Uzupełnienie danych
        print("\n📝 Krok 2: Uzupełnienie brakujących danych")
        self.send_message("1500 PLN na klient@firma.pl")

        # Krok 3: Wykonanie
        print("\n⚡ Krok 3: Wykonanie workflow")
        self.send_message("uruchom")

        # Podsumowanie
        print("\n📊 Podsumowanie konwersacji:")
        print(f"   ID konwersacji: {self.conversation_id}")
        print(f"   Liczba wiadomości: {len(self.history)}")
        print("   Status: Zakończona sukcesem")

    def run_interactive(self):
        """Uruchom tryb interaktywny."""
        print("=== Interaktywny Tryb Konwersacji ===")
        print("Wpisz 'quit' aby zakończyć\n")

        while True:
            try:
                text = input("👤 Ty: ").strip()
                if text.lower() in ["quit", "exit", "koniec"]:
                    break

                if not self.conversation_id:
                    self.start(text)
                else:
                    self.send_message(text)

            except KeyboardInterrupt:
                print("\n👋 Do widzenia!")
                break
            except Exception as e:
                print(f"❌ Błąd: {e}")


def main():
    """Główna funkcja przykładu."""

    import argparse
    parser = argparse.ArgumentParser(description="Przykład konwersacyjnego flow")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Uruchom tryb interaktywny")
    args = parser.parse_args()

    flow = ConversationFlow()

    if args.interactive:
        flow.run_interactive()
    else:
        flow.run_demo()


if __name__ == "__main__":
    main()
