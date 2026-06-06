"""
LLM enrichment for quality-required fields.

Rules + mapper extract intent and recipient; when body/subject are missing,
an optional LLM compose step fills entities.message / entities.subject
from the original user text. The mapper still builds DSL deterministically.
"""

from __future__ import annotations

import logging
import os

from app.registry import get_quality_required_fields
from app.schemas import NLPEntities, NLPResult

log = logging.getLogger("nlp.enrich")

# config field → entity field
_FIELD_TO_ENTITY = {
    "body": "message",
    "message": "message",
    "subject": "subject",
}


def is_enrich_enabled() -> bool:
    try:
        from app.conversation.system_map import get_doql_context

        ctx = get_doql_context()
        if ctx is not None:
            return bool(ctx.process.nlp_enrich_missing)
    except Exception:
        pass
    return os.getenv("NLP_ENRICH_MISSING", "0").strip().lower() in ("1", "true", "yes")


def get_enrichable_missing(missing_fields: list[str]) -> list[str]:
    """Return missing refs (action.field) that are quality fields we can compose."""
    enrichable: list[str] = []
    for ref in missing_fields:
        if "." not in ref:
            continue
        action, field = ref.split(".", 1)
        if field in _FIELD_TO_ENTITY and field in get_quality_required_fields(action):
            enrichable.append(ref)
    return enrichable


def can_enrich_missing(missing_fields: list[str]) -> bool:
    if not missing_fields or not is_enrich_enabled():
        return False
    from app.routing.parser.llm import _detect_provider

    if _detect_provider() == "none":
        return False
    enrichable = get_enrichable_missing(missing_fields)
    return len(enrichable) == len(missing_fields)


async def enrich_entities(nlp: NLPResult, missing_fields: list[str]) -> NLPResult | None:
    """Use LLM to compose missing quality fields. Returns updated NLPResult or None."""
    if not can_enrich_missing(missing_fields):
        return None

    fields_needed = sorted({ref.split(".", 1)[1] for ref in missing_fields})
    actions = {ref.split(".", 1)[0] for ref in missing_fields}
    entities = nlp.entities.model_dump(exclude_none=True)

    notify_actions = {"notify_slack", "notify_telegram", "notify_teams"}
    is_notify = bool(actions & notify_actions)

    if is_notify:
        system_prompt = """Jesteś asystentem piszącym krótkie powiadomienia (Slack/Telegram/Teams) po polsku.
Na podstawie prośby użytkownika uzupełnij brakujące pole message.
Zwróć TYLKO JSON bez markdown: {"message": "..."}
Wiadomość: 1-2 zdania, konkretna, bez powitania."""
        user_prompt = f"""Oryginalna prośba:
"{nlp.raw_text}"

Kontekst:
- kanał/chat: {entities.get('channel') or entities.get('chat_id', 'nieznany')}
- brakujące pola: {', '.join(fields_needed)}

Napisz treść powiadomienia."""
    else:
        system_prompt = """Jesteś asystentem piszącym treść wiadomości e-mail po polsku.
Na podstawie oryginalnej prośby użytkownika uzupełnij brakujące pola.
Zwróć TYLKO JSON bez markdown:
{"subject": "...", "message": "..."}
Pole message to treść e-maila (body). Bądź zwięzły (2-4 zdania), profesjonalny."""
        user_prompt = f"""Oryginalna prośba użytkownika:
"{nlp.raw_text}"

Kontekst:
- odbiorca (to): {entities.get('to', 'nieznany')}
- temat (subject): {entities.get('subject', 'brak')}
- brakujące pola: {', '.join(fields_needed)}

Uzupełnij brakujące pola zgodnie z intencją użytkownika."""

    try:
        from litellm import acompletion

        from app.routing.parser.llm import (
            LLM_API_BASE,
            LLM_MAX_TOKENS,
            LLM_MODEL,
            LLM_TEMPERATURE,
            _parse_json_response,
        )

        kwargs: dict = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": min(LLM_MAX_TOKENS, 512),
        }
        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = await acompletion(**kwargs)
        raw = response.choices[0].message.content
        parsed = _parse_json_response(raw)

        updates: dict = {}
        for ref in missing_fields:
            field = ref.split(".", 1)[1]
            entity_key = _FIELD_TO_ENTITY.get(field)
            if not entity_key:
                continue
            value = parsed.get(entity_key) or parsed.get(field)
            if isinstance(value, str) and value.strip():
                updates[entity_key] = value.strip()

        if not updates:
            log.warning("LLM enrich returned no usable fields")
            return None

        merged = {**entities, **updates}
        log.info("LLM enriched fields: %s", list(updates.keys()))
        return nlp.model_copy(
            update={"entities": NLPEntities(**merged)},
        )
    except Exception:
        log.exception("LLM enrichment failed")
        return None
