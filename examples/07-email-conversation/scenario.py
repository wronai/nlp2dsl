"""Scenariusz: e-mail z uzupełnianiem brakującego body przez dialog."""

from __future__ import annotations

from typing import Any, Optional

from nlp2dsl_sdk.client import ConversationFlow, NLP2DSLClient
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
    flow.send_message(
        "Treść wiadomości: W załączeniu podsumowanie tygodnia. "
        "Wszystkie zadania zamknięte na czas."
    )
    flow.send_message("uruchom")

    return {
        "conversation_id": flow.conversation_id,
        "turns": len(flow.history),
    }
