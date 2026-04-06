"""
Rule-based NLP parser — działa BEZ LLM.

Używa regex + słownika aliasów do wyodrębnienia:
  - intent (akcja)
  - entities (parametry)
  - trigger (harmonogram)

Wystarczający na MVP, fallback gdy LLM niedostępny.
"""

from __future__ import annotations

import re
import logging

from .schemas import NLPResult, NLPIntent, NLPEntities
from .registry import (
    ACTIONS_REGISTRY,
    COMPOSITE_INTENTS,
    get_action_by_alias,
    get_trigger,
)

log = logging.getLogger("nlp.rules")


# ── Regex patterns ────────────────────────────────────────────

AMOUNT_PATTERN = re.compile(
    r"(\d[\d\s]*[\d.,]*)\s*(PLN|USD|EUR|GBP|zł|pln|usd|eur|gbp)?",
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

REPORT_TYPE_KEYWORDS = {
    "sprzedaż": "sales",
    "sprzedazy": "sales",
    "sprzedażowy": "sales",
    "sales": "sales",
    "hr": "hr",
    "kadrowy": "hr",
    "finansowy": "finance",
    "finanse": "finance",
    "finance": "finance",
    "marketing": "marketing",
    "miesięczny": "monthly_summary",
    "tygodniowy": "weekly_summary",
}

FORMAT_KEYWORDS = {"pdf": "pdf", "csv": "csv", "excel": "xlsx", "xlsx": "xlsx"}

SLACK_CHANNEL_PATTERN = re.compile(r"#[\w-]+")


# ── Main parser ───────────────────────────────────────────────


def parse_rules(text: str) -> NLPResult:
    """Parse text using rules — no LLM needed."""
    text_lower = text.lower()

    # 1. Detect actions
    detected_actions = _detect_actions(text_lower)

    # 2. Check composite intents
    intent_name = _resolve_intent(detected_actions)

    # 3. Extract entities
    entities = _extract_entities(text, text_lower)

    # 4. Detect trigger
    trigger = get_trigger(text_lower)
    if trigger != "manual":
        entities_dict = entities.model_dump()
        entities_dict["_trigger"] = trigger

    confidence = min(0.6 + 0.1 * len(detected_actions), 0.9) if detected_actions else 0.3

    return NLPResult(
        intent=NLPIntent(intent=intent_name, confidence=confidence),
        entities=entities,
        raw_text=text,
    )


def _detect_actions(text_lower: str) -> list[str]:
    """Detect all action matches in text."""
    found = []
    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias in meta["aliases"]:
            if alias in text_lower:
                if action_name not in found:
                    found.append(action_name)
                break
    return found


def _resolve_intent(actions: list[str]) -> str:
    """Resolve single or composite intent."""
    if not actions:
        return "unknown"

    if len(actions) == 1:
        return actions[0]

    # Check composite intents
    action_set = set(actions)
    for composite_name, composite_actions in COMPOSITE_INTENTS.items():
        if action_set == set(composite_actions):
            return composite_name

    # Fallback: join as composite
    return "_and_".join(sorted(actions))


def _extract_entities(text: str, text_lower: str) -> NLPEntities:
    """Extract entities from text using regex and keywords."""
    entities = NLPEntities()

    # Amount
    amount_match = AMOUNT_PATTERN.search(text)
    if amount_match:
        raw_amount = amount_match.group(1).replace(" ", "").replace(",", ".")
        try:
            entities.amount = float(raw_amount)
        except ValueError:
            pass
        currency = amount_match.group(2)
        if currency:
            entities.currency = currency.upper()
            if entities.currency in ("ZŁ",):
                entities.currency = "PLN"

    # Email
    email_match = EMAIL_PATTERN.search(text)
    if email_match:
        entities.to = email_match.group(0)

    # Report type
    for keyword, rtype in REPORT_TYPE_KEYWORDS.items():
        if keyword in text_lower:
            entities.report_type = rtype
            break

    # Format
    for keyword, fmt in FORMAT_KEYWORDS.items():
        if keyword in text_lower:
            entities.format = fmt
            break

    # Slack channel
    channel_match = SLACK_CHANNEL_PATTERN.search(text)
    if channel_match:
        entities.channel = channel_match.group(0)

    # ── param_aliases extraction (from registry) ─────────────
    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias_key, target in meta.get("param_aliases", {}).items():
            if alias_key in text_lower:
                if "=" in target:
                    field, value = target.split("=", 1)
                    _set_entity(entities, field, value)
                # else: alias_key maps to a field name — value comes from text

    # Fallback recipient heuristics
    if not entities.to:
        patterns = [
            r"do\s+([\w.]+@[\w.]+)",
            r"(?:menedżer|manager|szef|kierownik|dyrektor)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text_lower)
            if m:
                if "@" in (m.group(0) if m.lastindex is None else m.group(1)):
                    entities.to = m.group(1) if m.lastindex else m.group(0)
                break

    return entities


def _set_entity(entities: NLPEntities, field: str, value: str):
    """Set entity field if not already set."""
    current = getattr(entities, field, None)
    if current is None:
        try:
            setattr(entities, field, value)
        except Exception:
            pass
