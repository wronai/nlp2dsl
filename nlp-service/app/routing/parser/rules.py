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

REMINDER_SUBJECT_PATTERN = re.compile(
    r"przypomnij\s+\S+@\S+\s+o\s+(.+)$",
    re.IGNORECASE,
)

EMAIL_SUBJECT_PATTERN = re.compile(
    r"z\s+tematem\s+(.+?)(?:\s+i\s+|\s*$)",
    re.IGNORECASE,
)

EMAIL_COLON_BODY_PATTERN = re.compile(
    r"@[\w.-]+\s*:\s*(.+)$",
)

BODY_CONTENT_PATTERN = re.compile(
    r"(?:treść(?:\s+wiadomości)?|body|message)\s*:\s*(.+)$",
    re.IGNORECASE,
)

EMAIL_OFFER_PATTERN = re.compile(
    r"z\s+now[aą]\s+ofert[aą]",
    re.IGNORECASE,
)

REPORT_TYPE_KEYWORDS = {
    "sprzedaż": "sales",
    "sprzedazy": "sales",
    "sprzedażowy": "sales",
    "sales": "sales",
    "hr": "hr",
    "kadrowy": "hr",
    "kadr": "hr",
    "finansowy": "finance",
    "finanse": "finance",
    "finance": "finance",
    "finansów": "finance",
    "marketing": "marketing",
    "miesięczny": "monthly_summary",
    "tygodniowy": "weekly_summary",
}

FORMAT_KEYWORDS = {"pdf": "pdf", "csv": "csv", "excel": "xlsx", "xlsx": "xlsx"}

SLACK_CHANNEL_PATTERN = re.compile(r"#[\w-]+")
NOTIFY_COLON_MESSAGE_PATTERN = re.compile(
    r"(?:#\S+|general|chat\s+-?\d+|-?\d{6,})\s*:\s*(.+)$",
    re.IGNORECASE,
)
NOTIFY_ABOUT_PATTERN = re.compile(
    r"(?:powiadom|notify|wyślij|wyslij)(?:\s+\S+)*\s+(?:#\S+|general)\s+o\s+(.+)$",
    re.IGNORECASE,
)
TELEGRAM_CHAT_PATTERN = re.compile(
    r"(?:telegram(?:ie)?|na telegram|notify telegram|do telegramu)"
    r"|chat\s+(-?\d+)"
    r"|(?:^|\s)([@][\w_]+|-?\d{5,})\s*:",
    re.IGNORECASE,
)
TELEGRAM_CHAT_ID_PATTERN = re.compile(r"(-?\d{6,})")
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

    # Handle description for generate_code (rules mode)
    if intent_name == "generate_code" and not entities.description:
        entities.description = text
    if intent_name == "generate_code" and not entities.language:
        if "python" in text_lower:
            entities.language = "python"
        elif "javascript" in text_lower or "js" in text_lower:
            entities.language = "javascript"
        elif "java" in text_lower:
            entities.language = "java"
    if intent_name == "crm_update" and not entities.entity:
        for kw, ent in (("lead", "lead"), ("kontakt", "contact"), ("contact", "contact"), ("klient", "client"), ("deal", "deal")):
            if kw in text_lower:
                entities.entity = ent
                break

    return NLPResult(
        intent=NLPIntent(intent=intent_name, confidence=confidence),
        entities=entities,
        raw_text=text,
    )


def _detect_actions(text_lower: str) -> list[str]:
    """Detect all action matches in text. Prefers longest alias match."""
    scores = _action_alias_scores(text_lower)
    if not scores:
        return []

    scores = _apply_context_filters(text_lower, scores)
    sorted_actions = _actions_by_score(scores)

    business = [a for a in sorted_actions if _action_category(a) == "business"]
    if len(business) >= _MIN_ACTIONS_FOR_DOMINANCE:
        return business

    dominant_action = _dominant_overlap_action(sorted_actions, scores)
    if dominant_action:
        return [dominant_action]
    return sorted_actions


def _apply_context_filters(text_lower: str, scores: dict[str, int]) -> dict[str, int]:
    """Suppress false positives and add implicit actions from context."""
    filtered = dict(scores)

    if any(k in text_lower for k in ("crm", "lead", "kontakt", "contact", "deal")):
        filtered.pop("system_status", None)
        filtered.pop("system_file_list", None)
        if not any(
            k in text_lower
            for k in ("wyślij email", "wyslij email", "napisz do", "send email", "maila do", "wiadomość do")
        ):
            filtered.pop("send_email", None)

    if "telegram" in text_lower:
        filtered.pop("notify_slack", None)
        if "notify_telegram" not in filtered:
            filtered["notify_telegram"] = 8

    if SLACK_CHANNEL_PATTERN.search(text_lower) and "notify_slack" not in filtered:
        if any(k in text_lower for k in ("powiadom", "wyślij", "wyslij", "slack", "#")):
            filtered["notify_slack"] = max(filtered.get("notify_slack", 0), 6)

    if "python" in text_lower or "javascript" in text_lower or "funkcj" in text_lower:
        if "generate_code" not in filtered and any(
            k in text_lower for k in ("napisz", "stwórz", "generuj kod", "program", "kod")
        ):
            filtered["generate_code"] = max(filtered.get("generate_code", 0), 10)

    for business in ("generate_report", "send_invoice", "send_email", "crm_update"):
        biz_score = filtered.get(business, 0)
        if biz_score >= 6:
            for sys_action in ("system_file_list", "system_status", "system_registry_list"):
                if filtered.get(sys_action, 0) < biz_score:
                    filtered.pop(sys_action, None)

    return filtered


def _action_alias_scores(text_lower: str) -> dict[str, int]:
    """Return best alias length per action."""
    scores: dict[str, int] = {}
    for action_name, meta in ACTIONS_REGISTRY.items():
        score = _longest_alias_match(text_lower, meta.get("aliases") or [])
        if score:
            scores[action_name] = score
    return scores


def _alias_in_text(text_lower: str, alias_text: str) -> bool:
    """Match alias; short tokens use word boundaries to avoid 'ls' in 'formacie'."""
    if " " in alias_text:
        return alias_text in text_lower
    if len(alias_text) <= 4:
        return bool(re.search(rf"(?<!\w){re.escape(alias_text)}(?!\w)", text_lower))
    return alias_text in text_lower


def _longest_alias_match(text_lower: str, aliases: list[str]) -> int:
    best_score = 0
    for alias in aliases:
        alias_text = str(alias).lower()
        if _alias_in_text(text_lower, alias_text) and len(alias_text) > best_score:
            best_score = len(alias_text)
    return best_score


def _actions_by_score(scores: dict[str, int]) -> list[str]:
    """Sort by best alias length, descending."""
    return sorted(scores.keys(), key=lambda action: scores[action], reverse=True)


def _dominant_overlap_action(
    sorted_actions: list[str],
    scores: dict[str, int],
) -> str | None:
    if len(sorted_actions) < _MIN_ACTIONS_FOR_DOMINANCE:
        return None

    top_action, second_action = sorted_actions[:2]
    top_score = scores[top_action]
    second_score = scores[second_action]
    top_category = _action_category(top_action)
    second_category = _action_category(second_action)

    if _top_system_action_wins(top_category, second_category, top_score, second_score):
        return top_action
    if _second_system_action_wins(top_category, second_category, top_score, second_score):
        return second_action
    return None


def _action_category(action_name: str) -> str:
    return str(ACTIONS_REGISTRY[action_name].get("category", "business"))


def _top_system_action_wins(
    top_category: str,
    second_category: str,
    top_score: int,
    second_score: int,
) -> bool:
    if top_category == "system" and second_category == "system":
        return top_score > second_score
    return top_category == "system" and second_category == "mullm"


def _second_system_action_wins(
    top_category: str,
    second_category: str,
    top_score: int,
    second_score: int,
) -> bool:
    return (
        top_category == "mullm"
        and second_category == "system"
        and top_score <= second_score
    )


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

    _extract_amount(entities, text)
    _extract_email(entities, text)
    _extract_body_content_prefix(entities, text)
    _extract_email_subject_and_body(entities, text)
    _extract_reminder_subject(entities, text)
    _extract_report_type(entities, text_lower)
    _extract_format(entities, text_lower)
    _extract_notification_channels(entities, text)
    _extract_notification_message(entities, text)
    _extract_param_aliases(entities, text_lower)
    _extract_system_entities(entities, text, text_lower)
    _extract_fallback_recipient(entities, text_lower)

    return entities


def _extract_amount(entities: NLPEntities, text: str) -> None:
    """Extract amount and currency from text."""
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


def _extract_email(entities: NLPEntities, text: str) -> None:
    """Extract email address(es) from text."""
    emails = EMAIL_PATTERN.findall(text)
    if not emails:
        return
    entities.to = emails[0]
    if len(emails) >= 2:
        entities.email_to = emails[1]


def _extract_body_content_prefix(entities: NLPEntities, text: str) -> None:
    """Extract body from 'Treść:' / 'Treść wiadomości:' follow-up phrases."""
    if entities.message:
        return
    match = BODY_CONTENT_PATTERN.search(text.strip())
    if match:
        body = match.group(1).strip()
        if body:
            entities.message = body


def _extract_email_subject_and_body(entities: NLPEntities, text: str) -> None:
    """Extract subject/body from common Polish email phrasing."""
    colon_match = EMAIL_COLON_BODY_PATTERN.search(text.strip())
    if colon_match:
        body = colon_match.group(1).strip()
        if body:
            entities.message = body
        return

    subject_match = EMAIL_SUBJECT_PATTERN.search(text)
    if subject_match:
        subject = subject_match.group(1).strip()
        if subject:
            entities.subject = subject

    if EMAIL_OFFER_PATTERN.search(text):
        if not entities.subject:
            entities.subject = "Nowa oferta"
        if not entities.message:
            entities.message = (
                "Dzień dobry,\n\nW załączeniu przesyłamy nową ofertę. "
                "Prosimy o kontakt w razie pytań.\n\nPozdrawiamy"
            )


def _extract_reminder_subject(entities: NLPEntities, text: str) -> None:
    """Extract email subject/body from 'Przypomnij X o Y' phrasing."""
    match = REMINDER_SUBJECT_PATTERN.search(text.strip())
    if not match:
        return
    subject = match.group(1).strip()
    if not subject:
        return
    entities.subject = subject[:1].upper() + subject[1:]
    if not entities.message:
        entities.message = f"Przypominamy: {entities.subject}."


def _extract_report_type(entities: NLPEntities, text_lower: str) -> None:
    """Extract report type from keywords."""
    for keyword, rtype in REPORT_TYPE_KEYWORDS.items():
        if keyword in text_lower:
            entities.report_type = rtype
            break


def _extract_format(entities: NLPEntities, text_lower: str) -> None:
    """Extract format from keywords."""
    for keyword, fmt in FORMAT_KEYWORDS.items():
        if keyword in text_lower:
            entities.format = fmt
            break


def _extract_notification_channels(entities: NLPEntities, text: str) -> None:
    """Extract Slack, Telegram, and Teams channels from text."""
    # Slack channel
    channel_match = SLACK_CHANNEL_PATTERN.search(text)
    if channel_match:
        entities.channel = channel_match.group(0)

    # Telegram chat_id
    if re.search(r"telegram", text, re.IGNORECASE):
        id_match = TELEGRAM_CHAT_ID_PATTERN.search(text)
        if id_match and not entities.chat_id:
            entities.chat_id = id_match.group(1)
        elif not entities.chat_id:
            telegram_match = TELEGRAM_CHAT_PATTERN.search(text)
            if telegram_match and telegram_match.lastindex:
                entities.chat_id = telegram_match.group(telegram_match.lastindex)

    # Teams channel (fallback when user explicitly names Teams)
    teams_match = TEAMS_CHANNEL_PATTERN.search(text)
    if teams_match and not entities.channel:
        entities.channel = teams_match.group(1)


def _extract_notification_message(entities: NLPEntities, text: str) -> None:
    """Extract Slack/Telegram/Teams message body from common phrasing."""
    if entities.message:
        return

    colon_match = NOTIFY_COLON_MESSAGE_PATTERN.search(text.strip())
    if colon_match:
        msg = colon_match.group(1).strip()
        if msg:
            entities.message = msg
            return

    about_match = NOTIFY_ABOUT_PATTERN.search(text.strip())
    if about_match:
        msg = about_match.group(1).strip()
        if msg:
            entities.message = msg


def _extract_param_aliases(entities: NLPEntities, text_lower: str) -> None:
    """Extract entities from registry param_aliases."""
    for action_name, meta in ACTIONS_REGISTRY.items():
        for alias_key, target in meta.get("param_aliases", {}).items():
            if _alias_in_text(text_lower, alias_key):
                if "=" in target:
                    field, value = target.split("=", 1)
                    _set_entity(entities, field, value)
                # else: alias_key maps to a field name — value comes from text


def _extract_system_entities(entities: NLPEntities, text: str, text_lower: str) -> None:
    """Extract system-related entities (file path, settings, model, mode)."""
    _extract_file_path_entity(entities, text)
    _extract_setting_path_entity(entities, text)
    _extract_model_setting_entity(entities, text_lower)
    _extract_numeric_setting_value(entities, text_lower)
    _extract_mode_setting_entity(entities, text_lower)


def _extract_file_path_entity(entities: NLPEntities, text: str) -> None:
    file_match = FILE_PATH_PATTERN.search(text)
    if file_match and not entities.file_path:
        entities.file_path = file_match.group(1)


def _extract_setting_path_entity(entities: NLPEntities, text: str) -> None:
    setting_match = SETTING_PATH_PATTERN.search(text)
    if setting_match and not entities.setting_path:
        entities.setting_path = setting_match.group(1)


def _extract_model_setting_entity(entities: NLPEntities, text_lower: str) -> None:
    for model_alias, model_full in MODEL_NAMES.items():
        if model_alias in text_lower:
            if not entities.setting_value:
                entities.setting_value = model_full
            if not entities.setting_path:
                entities.setting_path = "llm.model"
            break


def _extract_numeric_setting_value(entities: NLPEntities, text_lower: str) -> None:
    if not entities.setting_value:
        val_match = re.search(r"(?:na|do|=)\s*([0-9.]+)", text_lower)
        if val_match:
            entities.setting_value = val_match.group(1)


def _extract_mode_setting_entity(entities: NLPEntities, text_lower: str) -> None:
    mode_keywords = {"rules": "rules", "llm": "llm", "auto": "auto"}
    for kw, mode_val in mode_keywords.items():
        if f"tryb {kw}" in text_lower or f"mode {kw}" in text_lower:
            if not entities.setting_value:
                entities.setting_value = mode_val
            if not entities.setting_path:
                entities.setting_path = "nlp.default_mode"
            break


def _extract_fallback_recipient(entities: NLPEntities, text_lower: str) -> None:
    """Extract recipient using fallback heuristics."""
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


def _set_entity(entities: NLPEntities, field: str, value: str) -> None:
    """Set entity field if not already set."""
    current = getattr(entities, field, None)
    if current is None:
        try:
            setattr(entities, field, value)
        except Exception:
            pass
