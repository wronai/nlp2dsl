"""Scenariusz: konwersacyjny flow faktury — logika przykładu 05."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient


def run_demo(client: Optional[NLP2DSLClient] = None) -> None:
    flow = ConversationFlow(client)
    print("=== Demonstracja Konwersacyjnego Flow ===\n")

    try:
        flow.client.health()
    except Exception:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        return

    print("🚀 Krok 1: Inicjalizacja konwersacji")
    flow.start("Chcę wysłać fakturę")

    print("\n📝 Krok 2: Uzupełnienie brakujących danych")
    flow.send_message("1500 PLN na klient@firma.pl")

    print("\n⚡ Krok 3: Wykonanie workflow")
    flow.send_message("uruchom")

    print("\n📊 Podsumowanie konwersacji:")
    print(f"   ID konwersacji: {flow.conversation_id}")
    print(f"   Liczba wiadomości: {len(flow.history)}")
    print("   Status: Zakończona sukcesem")


def run_interactive(client: Optional[NLP2DSLClient] = None) -> None:
    ConversationFlow(client).run_interactive()


def run(client: Optional[NLP2DSLClient] = None, *, interactive: bool = False) -> Any:
    if interactive:
        run_interactive(client)
        return {}
    run_demo(client)
    return {}
