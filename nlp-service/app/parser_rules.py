"""
Rule-based NLP parser — działa BEZ LLM.

Używa regex + słownika aliasów do wyodrębnienia:
  - intent (akcja)
  - entities (parametry)
  - trigger (harmonogram)

Wystarczający na MVP, fallback gdy LLM niedostępny.
"""

import logging
import re

from app.registry import (
    ACTIONS_REGISTRY,
    COMPOSITE_INTENTS,
    get_trigger,
)
from app.schemas import NLPEntities, NLPIntent, NLPResult

log = logging.getLogger("nlp.rules")

_MIN_ACTIONS_FOR_DOMINANCE: int = 2


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
TELEGRAM_CHAT_PATTERN = re.compile(r"(?:telegram(?:ie)?|na telegram|do telegramu|chat(?:em)?|do)\s+([@][\w_]+|\d+)", re.IGNORECASE)
TEAMS_CHANNEL_PATTERN = re.compile(r"(?:teams|microsoft teams|na teams|do teamsu)\s+([#\w-]+)", re.IGNORECASE)

# ── System patterns ───────────────────────────────────────────

FILE_PATH_PATTERN = re.compile(
    r"(?:^|[\s\"'])([a-zA-Z0-9_./-]+\.\w{1,5})(?:[\s\"']|$)"
)

SETTING_PATH_PATTERN = re.compile(
    r"(llm\.(?:model|provider|temperature|max_tokens|fallback_threshold)"
    r"|nlp\.(?:default_mode|default_language|confidence_threshold)"
    r"|worker\.(?:timeout_seconds|retry_count|fail_fast)"
    r"|file_access\.(?:max_file_size_kb))"
)

MODEL_NAMES = {
    "gpt-5-mini": "openrouter/openai/gpt-5-mini",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4": "gpt-4",
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude": "claude-sonnet-4-20250514",
    "llama3": "ollama/llama3",
    "llama": "ollama/llama3",
    "mistral": "mistral/mistral-small-latest",
    "groq": "groq/llama-3.1-8b-instant",
}


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
    """Detect all action matches in text. Prefers longest alias match."""
    scores: dict[str, int] = {}  # action → longest alias length

    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias in meta["aliases"]:
            if alias in text_lower:
                current_score = scores.get(action_name, 0)
                if len(alias) > current_score:
                    scores[action_name] = len(alias)

    if not scores:
        return []

    # Sort by score descending — highest-scoring action first
    sorted_actions = sorted(scores.keys(), key=lambda a: scores[a], reverse=True)

    # If top action is system and has much higher score, return only it
    if len(sorted_actions) >= _MIN_ACTIONS_FOR_DOMINANCE:
        top_score = scores[sorted_actions[0]]
        second_score = scores[sorted_actions[1]]
        top_cat = ACTIONS_REGISTRY[sorted_actions[0]].get("category", "business")
        second_cat = ACTIONS_REGISTRY[sorted_actions[1]].get("category", "business")

        # Same category system actions with overlapping aliases — pick best
        if top_cat == "system" and second_cat == "system" and top_score > second_score:
            return [sorted_actions[0]]

    return sorted_actions


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

    # Telegram chat_id
    telegram_match = TELEGRAM_CHAT_PATTERN.search(text)
    if telegram_match and not entities.chat_id:
        entities.chat_id = telegram_match.group(1)

    # Teams channel (fallback when user explicitly names Teams)
    teams_match = TEAMS_CHANNEL_PATTERN.search(text)
    if teams_match and not entities.channel:
        entities.channel = teams_match.group(1)

    # ── param_aliases extraction (from registry) ─────────────
    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias_key, target in meta.get("param_aliases", {}).items():
            if alias_key in text_lower:
                if "=" in target:
                    field, value = target.split("=", 1)
                    _set_entity(entities, field, value)
                # else: alias_key maps to a field name — value comes from text

    # ── System entity extraction ──────────────────────────────

    # File path
    file_match = FILE_PATH_PATTERN.search(text)
    if file_match and not entities.file_path:
        entities.file_path = file_match.group(1)

    # Setting path (explicit like "llm.model")
    setting_match = SETTING_PATH_PATTERN.search(text)
    if setting_match and not entities.setting_path:
        entities.setting_path = setting_match.group(1)

    # Model name detection → setting_value
    for model_alias, model_full in MODEL_NAMES.items():
        if model_alias in text_lower:
            if not entities.setting_value:
                entities.setting_value = model_full
            if not entities.setting_path:
                entities.setting_path = "llm.model"
            break

    # Numeric value after "na" / "do" / "=" for settings
    if not entities.setting_value:
        val_match = re.search(r"(?:na|do|=)\s*([0-9.]+)", text_lower)
        if val_match:
            entities.setting_value = val_match.group(1)

    # Mode keywords for settings
    mode_keywords = {"rules": "rules", "llm": "llm", "auto": "auto"}
    for kw, mode_val in mode_keywords.items():
        if f"tryb {kw}" in text_lower or f"mode {kw}" in text_lower:
            if not entities.setting_value:
                entities.setting_value = mode_val
            if not entities.setting_path:
                entities.setting_path = "nlp.default_mode"

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


def _set_entity(entities: NLPEntities, field: str, value: str) -> None:
    """Set entity field if not already set."""
    current = getattr(entities, field, None)
    if current is None:
        try:
            setattr(entities, field, value)
        except Exception:
            pass
