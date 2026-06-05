"""Scenariusz: tryb interaktywny — rozmowa z nlp2dsl w terminalu."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient
from nlp2dsl_sdk.conversation_artifacts import write_conversation_artifacts


HELP = """
Komendy w trybie interaktywnym:
  • Wpisz intencję: „Chcę wysłać fakturę”, „Wyślij email do …”
  • Uzupełnij brakujące pola gdy system zapyta
  • „uruchom” / „wykonaj” — start workflow gdy status=ready
  • quit / exit / koniec — wyjście
"""


def run_demo(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    """Krótka demonstracja bez input() — do run-all.sh."""
    flow = ConversationFlow(client)
    print("=== Przykład: Interaktywny chat (demo skryptowane) ===\n")
    print("💡 Pełny tryb interaktywny: python3 main.py --interactive\n")

    flow.start("Wyślij email do team@firma.pl z tematem Status projektu")
    # Jeśli brak body — uzupełnij w drugiej turze
    flow.send_message("Treść: Projekt idzie zgodnie z planem, raport w załączniku.")
    if flow.history and "gotowy" not in flow.history[-1].get("text", "").lower():
        flow.send_message("uruchom")

    print(f"\n📊 conversation_id={flow.conversation_id}")
    write_conversation_artifacts(
        Path(__file__).resolve().parent / ".nlp2dsl",
        flow.export_trace(),
        scenario_name="scenario.py",
    )
    return {"conversation_id": flow.conversation_id}


def run_interactive(client: Optional[NLP2DSLClient] = None) -> None:
    print("=== Interaktywny chat z NLP2DSL ===")
    print(HELP)
    ConversationFlow(client).run_interactive()


def run(client: Optional[NLP2DSLClient] = None, *, interactive: bool = False) -> Any:
    if interactive:
        run_interactive(client)
        return {}
    return run_demo(client)
