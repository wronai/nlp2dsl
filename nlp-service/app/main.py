"""
NLP Service — pipeline: tekst → intent/entities → DSL.

Trzy tryby:
  - "rules" — offline, regex + aliasy (domyślny na MVP)
  - "llm"   — LLM API (OpenAI / Anthropic / Ollama)
  - "auto"  — rules first, LLM fallback jeśli confidence < 0.5

Endpoints:
  POST /nlp/parse     → NLPResult (intent + entities)
  POST /nlp/to-dsl    → DialogResponse (workflow DSL lub missing fields)
  GET  /nlp/actions   → lista dostępnych akcji + aliasów
  GET  /health        → status
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import NLPRequest, NLPResult, DialogResponse, ConversationResponse, ActionFormSchema
from .parser_rules import parse_rules
from .parser_llm import parse_llm, _detect_provider, LLM_MODEL
from .mapper import map_to_dsl
from .registry import ACTIONS_REGISTRY
from .orchestrator import (
    start_conversation,
    continue_conversation,
    get_conversation,
    get_action_form,
    FIELD_TYPES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("nlp-service")

app = FastAPI(
    title="NLP → DSL Service",
    description=(
        "Pipeline NLP do automatyzacji:\n\n"
        "**LLM rozumie → Pydantic waliduje → Mapper buduje → Docker wykonuje**"
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_FALLBACK_THRESHOLD = float(os.getenv("LLM_FALLBACK_THRESHOLD", "0.5"))


# ── Endpoints ─────────────────────────────────────────────────


@app.post("/nlp/parse", response_model=NLPResult)
async def parse_text(req: NLPRequest):
    """
    Etap 1: tekst → intent + entities.
    Nie generuje DSL — tylko rozumie język naturalny.
    """
    nlp_result = await _run_parser(req)
    return nlp_result


@app.post("/nlp/to-dsl", response_model=DialogResponse)
async def text_to_dsl(req: NLPRequest):
    """
    Pełny pipeline: tekst → NLP → DSL.
    Zwraca gotowy workflow lub listę brakujących pól.
    """
    nlp_result = await _run_parser(req)

    if nlp_result.intent.intent == "unknown":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Nie rozpoznano intencji",
                "text": req.text,
                "hint": "Spróbuj np. 'Wyślij fakturę na 1500 PLN do klient@firma.pl'",
            },
        )

    dialog = map_to_dsl(nlp_result)
    return dialog


@app.get("/nlp/actions")
async def list_actions():
    """Zwraca rejestr akcji z aliasami (vocabulary DSL)."""
    result = {}
    for name, meta in ACTIONS_REGISTRY.items():
        result[name] = {
            "description": meta["description"],
            "required": meta["required"],
            "optional": list(meta.get("optional", {}).keys()),
            "aliases": meta["aliases"],
        }
    return result


@app.get("/health")
async def health():
    llm_provider = _detect_provider()
    return {
        "status": "ok",
        "service": "nlp-service",
        "llm_engine": "litellm",
        "llm_provider": llm_provider if llm_provider != "none" else "disabled (rules only)",
        "llm_model": LLM_MODEL if llm_provider != "none" else None,
        "actions": list(ACTIONS_REGISTRY.keys()),
    }


# ── Conversation Loop (stanowy dialog) ───────────────────────


@app.post("/chat/start", response_model=ConversationResponse)
async def chat_start(body: dict):
    """
    Rozpocznij nową konwersację. System rozpoznaje intencję i dopytuje o brakujące dane.

    Body: {"text": "Wyślij fakturę na 1500 PLN"}
    """
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Field 'text' is required")

    return start_conversation(text)


@app.post("/chat/message", response_model=ConversationResponse)
async def chat_message(body: dict):
    """
    Kontynuuj rozmowę — uzupełnij brakujące dane.

    Body: {"conversation_id": "abc123", "text": "klient@firma.pl"}
    """
    cid = body.get("conversation_id", "")
    text = body.get("text", "")

    if not cid:
        raise HTTPException(status_code=400, detail="Field 'conversation_id' is required")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Field 'text' is required")

    return continue_conversation(cid, text)


@app.get("/chat/{conversation_id}")
async def chat_state(conversation_id: str):
    """Pobierz aktualny stan konwersacji."""
    state = get_conversation(conversation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return state.model_dump()


# ── Schema-driven UI ─────────────────────────────────────────


@app.get("/actions/schema")
async def actions_schema():
    """
    Zwraca pełny schemat formularzy dla wszystkich akcji.
    Frontend generuje UI dynamicznie z tego schematu.
    """
    schemas = {}
    for action_name in ACTIONS_REGISTRY:
        form = get_action_form(action_name)
        if form:
            schemas[action_name] = form.model_dump()
    return schemas


@app.get("/actions/schema/{action}", response_model=ActionFormSchema)
async def action_schema(action: str):
    """Zwraca schemat formularza dla konkretnej akcji."""
    form = get_action_form(action)
    if not form:
        raise HTTPException(status_code=404, detail=f"Action '{action}' not found")
    return form


# ── Settings API ─────────────────────────────────────────────


from .settings import settings_manager
from .system_executor import execute_system_action, SYSTEM_EXECUTORS


@app.get("/settings")
async def get_settings():
    """Pokaż wszystkie ustawienia systemu."""
    return {
        "settings": settings_manager.get_all(),
        "schema": settings_manager.describe(),
    }


@app.get("/settings/{section}")
async def get_settings_section(section: str):
    """Pokaż ustawienia sekcji (llm, nlp, worker, file_access)."""
    data = settings_manager.get_section(section)
    if not data:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not found")
    return {"section": section, "settings": data}


@app.put("/settings/{section}")
async def update_settings_section(section: str, body: dict):
    """Zaktualizuj ustawienia sekcji."""
    try:
        result = settings_manager.update_section(section, body)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/settings")
async def set_setting(body: dict):
    """Zmień pojedyncze ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}"""
    path = body.get("path", "")
    value = body.get("value")
    if not path:
        raise HTTPException(status_code=400, detail="Field 'path' is required")
    try:
        result = settings_manager.set(path, value)
        return result
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/settings/reset")
async def reset_settings(body: dict = {}):
    """Resetuj ustawienia. Body: {"section": "llm"} lub {} dla wszystkich."""
    section = body.get("section")
    return settings_manager.reset(section)


# ── System Execution API ─────────────────────────────────────


@app.post("/system/execute")
async def system_execute(body: dict):
    """
    Wykonaj akcję systemową bezpośrednio.
    Body: {"action": "system_file_list", "config": {"directory": "."}}
    """
    action = body.get("action", "")
    config = body.get("config", {})

    if action not in SYSTEM_EXECUTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown system action: '{action}'. Available: {list(SYSTEM_EXECUTORS.keys())}",
        )

    result = await execute_system_action(action, config)
    return result


# ── Internal ──────────────────────────────────────────────────


async def _run_parser(req: NLPRequest) -> NLPResult:
    """Execute parser according to mode."""
    mode = req.mode

    if mode == "rules":
        return parse_rules(req.text)

    if mode == "llm":
        provider = _detect_provider()
        if provider == "none":
            raise HTTPException(
                status_code=503,
                detail="No LLM provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_URL.",
            )
        return await parse_llm(req.text)

    # mode == "auto": rules first, LLM fallback
    rules_result = parse_rules(req.text)

    if rules_result.intent.confidence >= LLM_FALLBACK_THRESHOLD:
        log.info("Rules parser sufficient (confidence=%.2f)", rules_result.intent.confidence)
        return rules_result

    # Try LLM if available
    provider = _detect_provider()
    if provider != "none":
        log.info("Rules confidence too low (%.2f), trying LLM…", rules_result.intent.confidence)
        llm_result = await parse_llm(req.text)
        if llm_result.intent.confidence > rules_result.intent.confidence:
            return llm_result

    return rules_result
