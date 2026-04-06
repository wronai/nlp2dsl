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

from __future__ import annotations

import logging
from uuid import uuid4

from .schemas import (
    ConversationState,
    ConversationResponse,
    NLPEntities,
    NLPResult,
    NLPIntent,
    ActionFormSchema,
    FieldSchema,
    WorkflowDSL,
)
from .parser_rules import parse_rules
from .mapper import map_to_dsl
from .registry import ACTIONS_REGISTRY, COMPOSITE_INTENTS, get_trigger

log = logging.getLogger("orchestrator")

# ── In-memory conversation store (MVP — Redis w produkcji) ────

_conversations: dict[str, ConversationState] = {}


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
}


# ── Public API ────────────────────────────────────────────────


def start_conversation(text: str) -> ConversationResponse:
    """Rozpocznij nową rozmowę od pierwszej wiadomości użytkownika."""
    state = ConversationState(id=uuid4().hex[:12])
    state.history.append({"role": "user", "text": text})

    _conversations[state.id] = state

    return _process_message(state, text)


def continue_conversation(conversation_id: str, text: str) -> ConversationResponse:
    """Kontynuuj istniejącą rozmowę — użytkownik uzupełnia brakujące dane."""
    state = _conversations.get(conversation_id)
    if not state:
        return ConversationResponse(
            conversation_id=conversation_id,
            status="error",
            message="Nie znaleziono rozmowy. Zacznij nową przez /chat/start.",
        )

    state.history.append({"role": "user", "text": text})

    return _process_message(state, text)


def get_conversation(conversation_id: str) -> ConversationState | None:
    """Pobierz stan rozmowy."""
    return _conversations.get(conversation_id)


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
    
    # 0. Check for execution commands first
    exec_triggers = ["uruchom", "execute", "wykonaj", "start", "run"]
    if text.lower().strip() in exec_triggers:
        if state.status == "ready" and state.dsl:
            # Execute the workflow
            state.status = "completed"
            msg = f"Workflow {state.dsl.name} uruchomiony."
            state.history.append({"role": "assistant", "text": msg})
            return ConversationResponse(
                conversation_id=state.id,
                status="completed",
                message=msg,
                dsl=state.dsl,
            )
        else:
            msg = "Nie ma gotowego workflow do uruchomienia. Uzupełnij najpierw wszystkie dane."
            state.history.append({"role": "assistant", "text": msg})
            return ConversationResponse(
                conversation_id=state.id,
                status="in_progress",
                message=msg,
            )

    # 1. NLP extraction
    nlp = parse_rules(text)
    log.info("NLP: intent=%s conf=%.2f", nlp.intent.intent, nlp.intent.confidence)

    # 2. Update state with new data
    _merge_into_state(state, nlp)

    # 3. Resolve actions for current intent
    if not state.intent or state.intent == "unknown":
        msg = "Nie rozpoznałem intencji. Jaką automatyzację chcesz stworzyć? Np. faktura, raport, email, powiadomienie Slack."
        state.history.append({"role": "assistant", "text": msg})
        return ConversationResponse(
            conversation_id=state.id,
            status="in_progress",
            message=msg,
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


def _merge_into_state(state: ConversationState, nlp: NLPResult):
    """Merge NLP result into conversation state (accumulate entities)."""

    # Update intent if we got a better one
    if nlp.intent.intent != "unknown":
        if state.intent is None or nlp.intent.confidence > 0.5:
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
