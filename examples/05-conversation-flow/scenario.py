"""Scenariusz: konwersacyjny flow faktury — logika przykładu 05."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient
from nlp2dsl_sdk.conversation_artifacts import write_conversation_artifacts
from nlp2dsl_sdk.conversation_artifacts import write_conversation_artifacts


def _save_conversation_artifacts(flow: ConversationFlow, example_dir: Path) -> None:
    artifact_root = example_dir / ".nlp2dsl"
    trace = flow.export_trace()
    write_conversation_artifacts(artifact_root, trace, scenario_name="scenario.py")


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
    _save_conversation_artifacts(flow, Path(__file__).resolve().parent)


def run_interactive(client: Optional[NLP2DSLClient] = None) -> None:
    ConversationFlow(client).run_interactive()


def run(client: Optional[NLP2DSLClient] = None, *, interactive: bool = False) -> Any:
    if interactive:
        run_interactive(client)
        return {}
    run_demo(client)
    return {}
