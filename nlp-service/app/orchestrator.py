"""
Conversation Orchestrator — stanowy dialog AI → DSL.

Wzorzec: AI as a state manager, not a generator.
  ❌ AI nie generuje workflow bez kontroli
  ✅ AI rozumie → dopytuje → uzupełnia stan → Mapper buduje DSL

Conversation flow:
  User → NLP → partial state → validation → missing?
    ↑                                          ↓
    └──────── pytanie (rules/LLM) ←────────────┘
"""

import logging
from uuid import uuid4

from app.mapper import map_to_dsl
from app.parser_rules import parse_rules
from app.registry import ACTIONS_REGISTRY, SYSTEM_ACTIONS, get_trigger
from app.schemas import (
    ActionFormSchema,
    ConversationResponse,
    ConversationState,
    FieldSchema,
    NLPEntities,
    NLPIntent,
    NLPResult,
)
from app.store.factory import get_conversation_store

log = logging.getLogger("orchestrator")

_store = get_conversation_store()

_CONVERSATION_ID_LENGTH: int = int("12")
_SYSTEM_RESULT_PREVIEW_LENGTH: int = int("2000")
_SYSTEM_FILE_LIST_LIMIT: int = int("30")
_MIN_INTENT_CONFIDENCE: float = 0.5


# ── Field type inference ──────────────────────────────────────

FIELD_TYPES: dict[str, dict] = {
    "amount":      {"type": "number",  "label": "Kwota"},
    "currency":    {"type": "select",  "label": "Waluta", "options": ["PLN", "EUR", "USD", "GBP"]},
    "to":          {"type": "email",   "label": "Adres e-mail odbiorcy"},
    "subject":     {"type": "string",  "label": "Temat wiadomości"},
    "message":     {"type": "string",  "label": "Treść wiadomości"},
    "body":        {"type": "string",  "label": "Treść"},
    "channel":     {"type": "string",  "label": "Kanał Slack (np. #general)"},
    "report_type": {"type": "select",  "label": "Typ raportu", "options": ["sales", "hr", "finance", "marketing"]},
    "format":      {"type": "select",  "label": "Format", "options": ["pdf", "csv", "xlsx"]},
    "entity":      {"type": "select",  "label": "Typ encji CRM", "options": ["contact", "client", "lead", "deal"]},
    "data":        {"type": "string",  "label": "Dane (JSON)"},
    # ── System fields ──
    "setting_path":       {"type": "string",  "label": "Ścieżka ustawienia (np. llm.model)"},
    "setting_value":      {"type": "string",  "label": "Nowa wartość"},
    "section":            {"type": "select",  "label": "Sekcja ustawień", "options": ["all", "llm", "nlp", "worker", "file_access"]},
    "file_path":          {"type": "string",  "label": "Ścieżka pliku"},
    "content":            {"type": "string",  "label": "Treść pliku"},
    "directory":          {"type": "string",  "label": "Katalog"},
    "pattern":            {"type": "string",  "label": "Wzorzec (np. *.py)"},
    "mode":               {"type": "select",  "label": "Tryb zapisu", "options": ["write", "append"]},
    "action_name":        {"type": "string",  "label": "Nazwa akcji"},
    "action_description": {"type": "string",  "label": "Opis akcji"},
    "required_fields":    {"type": "string",  "label": "Wymagane pola (przecinkami)"},
    "aliases":            {"type": "string",  "label": "Aliasy (przecinkami)"},
}


# ── Public API ────────────────────────────────────────────────


async def start_conversation(text: str) -> ConversationResponse:
    """Rozpocznij nową rozmowę od pierwszej wiadomości użytkownika."""
    state = ConversationState(id=uuid4().hex[:_CONVERSATION_ID_LENGTH])
    state.history.append({"role": "user", "text": text})

    result = _process_message(state, text)
    await _store.save(state.id, state.model_dump())
    return result


async def continue_conversation(conversation_id: str, text: str) -> ConversationResponse:
    """Kontynuuj istniejącą rozmowę — użytkownik uzupełnia brakujące dane.

    Jeśli rozmowa jeszcze nie istnieje, tworzona jest lazily, aby UI desktopowe
    i WebSocket mogły rozpocząć dialog bez wcześniejszego /chat/start.
    """
    raw = await _store.get(conversation_id)
    if not raw:
        log.info("Conversation %s not found; creating new state lazily", conversation_id)
        state = ConversationState(id=conversation_id)
    else:
        state = ConversationState(**raw)

    state.history.append({"role": "user", "text": text})

    result = _process_message(state, text)
    await _store.save(state.id, state.model_dump())
    return result


async def get_conversation(conversation_id: str) -> ConversationState | None:
    """Pobierz stan rozmowy."""
    raw = await _store.get(conversation_id)
    if raw:
        return ConversationState(**raw)
    return None


def get_action_form(action: str) -> ActionFormSchema | None:
    """Generuj formularz UI z registry (schema-driven UI)."""
    meta = ACTIONS_REGISTRY.get(action)
    if not meta:
        return None

    fields = []
    for field_name in meta["required"]:
        fmeta = FIELD_TYPES.get(field_name, {"type": "string", "label": field_name})
        fields.append(FieldSchema(
            name=field_name,
            type=fmeta["type"],
            label=fmeta["label"],
            required=True,
            options=fmeta.get("options", []),
        ))

    for field_name in meta.get("optional", {}):
        fmeta = FIELD_TYPES.get(field_name, {"type": "string", "label": field_name})
        default_val = meta["optional"][field_name]
        fields.append(FieldSchema(
            name=field_name,
            type=fmeta["type"],
            label=fmeta["label"],
            required=False,
            options=fmeta.get("options", []),
            default=str(default_val) if default_val else None,
        ))

    return ActionFormSchema(
        action=action,
        description=meta["description"],
        fields=fields,
    )


# ── Internal ──────────────────────────────────────────────────


def _process_message(state: ConversationState, text: str) -> ConversationResponse:
    """Core orchestration: parse → merge → validate → respond."""

    # 1. NLP extraction
    nlp = parse_rules(text)
    log.info("NLP: intent=%s conf=%.2f", nlp.intent.intent, nlp.intent.confidence)

    # 2. Update state with new data
    _merge_into_state(state, nlp)

    # 3. Resolve actions for current intent
    if not state.intent or state.intent == "unknown":
        msg = (
            "Nie rozpoznałem intencji. Jaką automatyzację chcesz stworzyć?\n"
            "Np. faktura, raport, email, powiadomienie Slack.\n"
            "Komendy systemowe: ustawienia, pokaż pliki, status, pomoc."
        )
        state.history.append({"role": "assistant", "text": msg})
        return ConversationResponse(
            conversation_id=state.id,
            status="in_progress",
            message=msg,
        )

    # 3b. System actions — execute immediately, no DSL
    if state.intent in SYSTEM_ACTIONS:
        from app.system_executor import SYSTEM_EXECUTORS

        config = {k: v for k, v in state.entities.items() if v is not None and k != "_trigger"}

        executor = SYSTEM_EXECUTORS.get(state.intent)
        if executor:
            try:
                inner_result = executor(config)
                result = {"action": state.intent, "status": "completed", "result": inner_result}
            except Exception as e:
                result = {"action": state.intent, "status": "failed", "error": str(e)}
        else:
            result = {"action": state.intent, "status": "failed", "error": "Executor not found"}

        state.status = "done"
        msg = _format_system_result(state.intent, result)
        state.history.append({"role": "assistant", "text": msg})

        return ConversationResponse(
            conversation_id=state.id,
            status="done",
            message=msg,
            dsl=None,
        )

    # 4. Try to build DSL
    nlp_for_mapper = NLPResult(
        intent=NLPIntent(intent=state.intent, confidence=1.0),
        entities=NLPEntities(**{k: v for k, v in state.entities.items() if k != "_trigger"}),
        raw_text=" ".join(h["text"] for h in state.history if h["role"] == "user"),
    )

    dialog = map_to_dsl(nlp_for_mapper)

    # 5. Check completeness
    if dialog.status == "complete" and dialog.workflow:
        state.dsl = dialog.workflow
        state.status = "ready"
        state.missing = []

        msg = f"Workflow gotowy: {dialog.workflow.name} ({len(dialog.workflow.steps)} kroków). Wyślij 'uruchom' aby wykonać."
        state.history.append({"role": "assistant", "text": msg})

        return ConversationResponse(
            conversation_id=state.id,
            status="ready",
            message=msg,
            dsl=dialog.workflow,
        )

    # 6. Incomplete — generate question + form
    state.missing = dialog.missing_fields
    question = dialog.prompt_user or "Podaj brakujące dane."

    # Build dynamic form for first missing action
    form = None
    if dialog.missing_fields:
        first_missing_action = dialog.missing_fields[0].split(".")[0]
        form = get_action_form(first_missing_action)

    state.history.append({"role": "assistant", "text": question})

    return ConversationResponse(
        conversation_id=state.id,
        status="in_progress",
        message=question,
        missing=dialog.missing_fields,
        form=form,
    )


def _merge_into_state(state: ConversationState, nlp: NLPResult) -> None:
    """Merge NLP result into conversation state (accumulate entities)."""

    # Update intent if we got a better one
    if nlp.intent.intent != "unknown":
        if state.intent is None or nlp.intent.confidence > _MIN_INTENT_CONFIDENCE:
            state.intent = nlp.intent.intent

    # Merge entities (new values override None, don't overwrite existing with None)
    new_entities = nlp.entities.model_dump(exclude_none=True)
    for key, value in new_entities.items():
        if value is not None:
            state.entities[key] = value

    # Detect trigger from accumulated text
    full_text = " ".join(h["text"] for h in state.history if h["role"] == "user")
    trigger = get_trigger(full_text)
    if trigger != "manual":
        state.entities["_trigger"] = trigger


# ── System result formatting ─────────────────────────────────


def _format_system_result(intent: str, result: dict) -> str:
    """Format system action result as human-readable message."""
    import json

    if result.get("status") == "failed":
        return f"Błąd: {result.get('error', 'nieznany')}"

    inner = result.get("result", result)

    if intent == "system_status":
        return (
            f"System v{inner.get('version', '?')}\n"
            f"LLM: {inner.get('llm_provider', '?')} / {inner.get('llm_model', '?')}\n"
            f"NLP: tryb {inner.get('nlp_mode', '?')}\n"
            f"Akcje: {inner.get('actions_business', 0)} biznesowych + {inner.get('actions_system', 0)} systemowych"
        )

    if intent == "system_settings_get":
        settings = inner.get("settings", inner)
        return f"Ustawienia:\n{json.dumps(settings, indent=2, ensure_ascii=False)}"

    if intent == "system_settings_set":
        return f"Zmieniono {inner.get('path', '?')}: {inner.get('old', '?')} → {inner.get('new', '?')}"

    if intent == "system_settings_reset":
        return f"Ustawienia zresetowane: {inner.get('reset', 'all')}"

    if intent == "system_file_read":
        if inner.get("error"):
            return f"Błąd: {inner['error']}"
        return (
            f"Plik: {inner.get('file_path', '?')} ({inner.get('size_kb', '?')} KB, {inner.get('lines', '?')} linii)\n"
            f"---\n{inner.get('content', '')[:_SYSTEM_RESULT_PREVIEW_LENGTH]}"
        )

    if intent == "system_file_write":
        if inner.get("error"):
            return f"Błąd: {inner['error']}"
        return f"Zapisano: {inner.get('file_path', '?')} ({inner.get('size_kb', '?')} KB)"

    if intent == "system_file_list":
        files = inner.get("files", [])
        lines = [f"Pliki w {inner.get('directory', '?')} ({inner.get('count', 0)}):"]
        for f in files[:_SYSTEM_FILE_LIST_LIMIT]:
            lines.append(f"  {f['path']} ({f['size_kb']} KB)")
        return "\n".join(lines)

    if intent == "system_registry_list":
        actions = inner.get("actions", {})
        lines = [f"Zarejestrowane akcje ({inner.get('count', 0)}):"]
        for name, meta in actions.items():
            cat = meta.get("category", "business")
            req = ", ".join(meta.get("required", []))
            lines.append(f"  [{cat}] {name}: {meta['description']} (required: {req or 'brak'})")
        return "\n".join(lines)

    if intent in ("system_registry_add", "system_registry_edit"):
        return f"Rejestr zaktualizowany: {json.dumps(inner, ensure_ascii=False)}"

    return json.dumps(inner, indent=2, ensure_ascii=False)
