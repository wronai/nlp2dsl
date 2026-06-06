"""Scenariusz: e-mail z uzupełnianiem brakującego body przez dialog."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient
from nlp2dsl_sdk.conversation_artifacts import write_conversation_artifacts
from nlp2dsl_sdk.preview import ensure_services, preview_text_examples


EMAIL_PROMPT = "Wyślij email do jan@example.com z tematem Podsumowanie tygodnia"


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: E-mail z uzupełnieniem danych w dialogu ===\n")

    if not ensure_services(client):
        return {}

    print("1️⃣  One-shot (bez dialogu) — pokazuje brakujące pole body:")
    preview_text_examples(client, "", [EMAIL_PROMPT], mode="rules")

    print("\n2️⃣  Ten sam przypadek przez conversation loop:")
    flow = ConversationFlow(client)
    flow.start(EMAIL_PROMPT)
    follow_up = flow.send_message(
        "Treść wiadomości: W załączeniu podsumowanie tygodnia. "
        "Wszystkie zadania zamknięte na czas."
    )
    if follow_up.get("status") == "ready":
        flow.send_message("uruchom")

    write_conversation_artifacts(
        Path(__file__).resolve().parent / ".nlp2dsl",
        flow.export_trace(),
        scenario_name="scenario.py",
    )

    return {
        "conversation_id": flow.conversation_id,
        "turns": len(flow.history),
    }
