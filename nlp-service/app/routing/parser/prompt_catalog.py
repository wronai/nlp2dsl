"""Dynamiczny katalog akcji dla promptu LLM — DOQL commands[] lub ACTIONS_REGISTRY."""

from __future__ import annotations

import json

from app.conversation.system_map import known_action_names
from app.registry import ACTIONS_REGISTRY, COMPOSITE_INTENTS


def build_llm_system_prompt() -> str:
    """Schemat intencji i pól generowany z rejestru (nie hardcoded)."""
    allowed = known_action_names()
    actions_lines: list[str] = []
    for name, meta in sorted(ACTIONS_REGISTRY.items()):
        if name not in allowed:
            continue
        req = ", ".join(meta.get("required", [])) or "brak"
        opt = ", ".join(meta.get("optional", {}).keys()) or "brak"
        quality = ", ".join(meta.get("quality_required", [])) or ""
        q_suffix = f", quality: {quality}" if quality else ""
        actions_lines.append(f"- {name}: {meta['description']} (required: {req}; optional: {opt}{q_suffix})")

    composite_lines = [
        f"- {name}: {' + '.join(steps)}"
        for name, steps in sorted(COMPOSITE_INTENTS.items())
    ]

    entity_fields = sorted(
        {
            "amount",
            "currency",
            "to",
            "email_to",
            "subject",
            "message",
            "channel",
            "chat_id",
            "report_type",
            "format",
            "entity",
            "data",
            "description",
            "language",
            "context",
            "include_tests",
            "setting_path",
            "setting_value",
            "file_path",
            "directory",
            "pattern",
            "action_name",
            "action_description",
        }
    )

    return f"""Jesteś silnikiem NLP do automatyzacji procesów biznesowych.

Twoim JEDYNYM zadaniem jest:
1. Rozpoznać INTENT (co użytkownik chce zrobić)
2. Wyodrębnić ENTITIES (parametry) z tekstu użytkownika
3. Wskazać MISSING (brakujące wymagane pola)

Zwracaj TYLKO poprawny JSON — bez markdown, bez komentarzy.

Dostępne akcje (intenty):
{chr(10).join(actions_lines)}

Złożone intenty (multi-step):
{chr(10).join(composite_lines)}

Pola entities (użyj null gdy brak):
{json.dumps({f: None for f in entity_fields}, indent=2)}

Mapowanie:
- body e-maila → entities.message
- chat_id Telegram → numer lub @handle
- description (generate_code) → pełne zadanie użytkownika
- data (crm) → obiekt JSON z polami rekordu

Schemat odpowiedzi:
{{
  "intent": {{"intent": "...", "confidence": 0.0-1.0}},
  "entities": {{...}},
  "missing": ["field1"]
}}"""
