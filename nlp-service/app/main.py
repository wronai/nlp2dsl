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

from http import HTTPStatus
import json
import logging
from typing import Any

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.audio_parser import StreamingSTT, is_stt_available, stt_audio
from app.code_generator import code_generator
from app.config import settings as _svc_settings
from app.logging_setup import RequestIDMiddleware, setup_logging
from app.dsl.pipeline import map_to_dsl_with_enrichment
from app.orchestrator import (
    continue_conversation,
    get_action_form,
    get_conversation,
    start_conversation,
)
from app.parser_llm import LLM_MODEL, _detect_provider, parse_llm
from app.parser_rules import parse_rules
from app.conversation.system_map import command_meta, known_action_names
from app.schemas import (
    ActionFormSchema,
    ConversationResponse,
    DialogResponse,
    NLPRequest,
    NLPResult,
    OrientRequest,
)
from app.settings import settings_manager
from app.store.factory import get_conversation_store
from app.system_executor import SYSTEM_EXECUTORS, execute_system_action


setup_logging(service="nlp-service")
log = logging.getLogger("nlp-service")

app = FastAPI(
    title="NLP → DSL Service",
    description=(
        "Pipeline NLP do automatyzacji:\n\n"
        "**LLM rozumie → Pydantic waliduje → Mapper buduje → Docker wykonuje**"
    ),
    version="0.1.0",
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_FALLBACK_THRESHOLD = _svc_settings.llm_fallback_threshold


# ── Endpoints ─────────────────────────────────────────────────


@app.post("/nlp/orient")
async def orient_text(req: OrientRequest) -> dict[str, Any]:
    """Orientacja zapytania (file_list / shell / workflow) — bez LLM, przed pełnym parse."""
    from app.routing.orientation import orient_query

    return orient_query(req.text, connector=req.connector).to_dict()


@app.post("/nlp/parse", response_model=NLPResult)
async def parse_text(req: NLPRequest) -> NLPResult:
    """
    Etap 1: tekst → intent + entities.
    Nie generuje DSL — tylko rozumie język naturalny.
    """
    return await _run_parser(req)


@app.post("/nlp/to-dsl", response_model=DialogResponse)
async def text_to_dsl(req: NLPRequest) -> DialogResponse:
    """
    Pełny pipeline: tekst → NLP → DSL.
    Zwraca gotowy workflow lub listę brakujących pól.
    """
    nlp_result = await _run_parser(req)

    if nlp_result.intent.intent == "unknown":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail={
                "error": "Nie rozpoznano intencji",
                "text": req.text,
                "hint": "Spróbuj np. 'Wyślij fakturę na 1500 PLN do klient@firma.pl'",
            },
        )

    return await map_to_dsl_with_enrichment(nlp_result)


@app.get("/nlp/access/config")
async def access_config() -> dict[str, Any]:
    """Załadowany nlp2dsl.yaml — obszary, agenci, grupy etykiet."""
    from app.access.config import get_access_config

    cfg = get_access_config()
    return {
        "path": cfg.path,
        "version": cfg.version,
        "default_agent": cfg.default_agent,
        "integrations": cfg.enabled_integrations,
        "resource_areas": [
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "uri_patterns": a.get("uri_patterns"),
                "labels": a.get("labels"),
                "actions": list((a.get("actions") or {}).keys()),
            }
            for a in cfg.resource_areas
        ],
        "agents": list(cfg.agents.keys()),
        "label_groups": cfg.label_groups,
        "native_routes": len(cfg.native_routes),
    }


@app.get("/nlp/access/check")
async def access_check(
    agent_id: str,
    action: str,
    resource_area: str | None = None,
    uri: str | None = None,
    permission_action: str = "execute",
) -> dict[str, Any]:
    """Sprawdź uprawnienie agenta (debug / integracja Mullm)."""
    from app.access.policy import authorize_action

    meta = command_meta(action)
    decision = authorize_action(
        agent_id,
        action,
        resource_area=resource_area or meta.get("resource_area"),
        uri=uri,
        permission_action=permission_action or meta.get("permission_action"),
        action_meta=meta,
    )
    return decision.to_dict()


@app.post("/nlp/access/reload")
async def access_reload() -> dict[str, str]:
    """Przeładuj nlp2dsl.yaml bez restartu."""
    from app.access.config import reload_access_config

    cfg = reload_access_config()
    return {"status": "ok", "path": cfg.path or ""}


@app.get("/nlp/actions")
async def list_actions() -> dict[str, Any]:
    """Zwraca rejestr akcji z aliasami (vocabulary DSL) — w zakresie DOQL gdy aktywne."""
    result = {}
    for name in sorted(known_action_names()):
        meta = command_meta(name)
        if not meta:
            continue
        optional = meta.get("optional", {})
        result[name] = {
            "description": meta.get("description", name),
            "required": list(meta.get("required", [])),
            "optional": list(optional.keys()) if isinstance(optional, dict) else list(optional),
            "aliases": list(meta.get("aliases", [])),
        }
    return result


@app.get("/health")
async def health() -> dict[str, Any]:
    from app.routing.observability import routing_metrics_snapshot

    llm_provider = _detect_provider()
    store = get_conversation_store()
    return {
        "status": "ok",
        "service": "nlp-service",
        "llm_engine": "litellm",
        "llm_provider": llm_provider if llm_provider != "none" else "disabled (rules only)",
        "llm_model": LLM_MODEL if llm_provider != "none" else None,
        "conversation_store": type(store).__name__,
        "active_conversations": await store.count(),
        "actions": sorted(known_action_names()),
        "routing_metrics": routing_metrics_snapshot(),
    }


# ── Conversation Loop (stanowy dialog) ───────────────────────


@app.post("/chat/start", response_model=ConversationResponse)
async def chat_start(
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
    doql_context_path: str = Form(default=""),
    context_json: str = Form(default=""),
) -> ConversationResponse:
    """
    Rozpocznij nową konwersację. System rozpoznaje intencję i dopytuje o brakujące dane.

    Obsługuje:
    - Tekst: Form field "text"
    - Audio: UploadFile (STT via Deepgram)

    Examples:
        # Tekst
        curl -X POST -F "text=Wyślij fakturę" http://localhost:8002/chat/start

        # Audio
        curl -X POST -F "audio=@file.wav" http://localhost:8002/chat/start
    """
    # Audio input (STT)
    if audio:
        if not is_stt_available():
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="STT not available. Set DEEPGRAM_API_KEY.",
            )
        audio_bytes = await audio.read()
        transcript = await stt_audio(audio_bytes)
        if not transcript:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Failed to transcribe audio",
            )
        text = transcript
        log.info("STT transcript: %s", text)

    # Text input
    if not text.strip():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'text' or 'audio' is required",
        )

    inline = _parse_context_json(context_json)
    return await start_conversation(
        text,
        doql_context_path=doql_context_path or None,
        context_inline=inline or None,
    )


def _parse_context_json(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


@app.post("/chat/message", response_model=ConversationResponse)
async def chat_message(
    conversation_id: str = Form(...),
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
    context_json: str = Form(default=""),
) -> ConversationResponse:
    """
    Kontynuuj rozmowę — uzupełnij brakujące dane.

    Obsługuje:
    - Tekst: Form field "text"
    - Audio: UploadFile (STT via Deepgram)

    Examples:
        # Tekst
        curl -X POST -F "conversation_id=abc123" -F "text=1500 PLN" http://localhost:8002/chat/message

        # Audio
        curl -X POST -F "conversation_id=abc123" -F "audio=@file.wav" http://localhost:8002/chat/message
    """
    # Audio input (STT)
    if audio:
        if not is_stt_available():
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="STT not available. Set DEEPGRAM_API_KEY.",
            )
        audio_bytes = await audio.read()
        transcript = await stt_audio(audio_bytes)
        if not transcript:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Failed to transcribe audio",
            )
        text = transcript
        log.info("STT transcript: %s", text)

    # Text input
    if not text.strip():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'text' or 'audio' is required",
        )

    inline = _parse_context_json(context_json)
    return await continue_conversation(conversation_id, text, context_inline=inline or None)


@app.get("/chat/{conversation_id}")
async def chat_state(conversation_id: str) -> dict[str, Any]:
    """Pobierz aktualny stan konwersacji."""
    state = await get_conversation(conversation_id)
    if not state:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Conversation not found")
    return state.model_dump()


@app.post("/chat/registry/observe")
async def chat_registry_observe(request: Request) -> dict[str, Any]:
    """
    Merge execution / entities into environment.doql.less (registry loop).

    Body: {"doql_context_path": "...", "phase": "executed", "execution": {...}, "intent": "...", "entities": {}}
    """
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    path_raw = body.get("doql_context_path") or body.get("doqlContextPath")
    if not path_raw:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="doql_context_path required")

    phase = str(body.get("phase") or "executed")
    execution = body.get("execution")
    entities = body.get("entities") or {}
    intent = body.get("intent")
    conversation_id = body.get("conversation_id")

    try:
        from app.conversation.doql_registry import refresh_registry_for_state
        from app.conversation.orchestrator import mark_conversation_executed
        from app.schemas import ConversationState

        if (
            conversation_id
            and phase == "executed"
            and isinstance(execution, dict)
        ):
            await mark_conversation_executed(str(conversation_id), execution)

        state = ConversationState(
            id=str(body.get("conversation_id") or "observe"),
            intent=intent,
            entities=dict(entities),
            doql_context_path=str(path_raw),
        )
        out = refresh_registry_for_state(
            state,
            phase=phase,
            execution=execution if isinstance(execution, dict) else None,
            explicit_path=str(path_raw),
        )
        if out is None:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Could not refresh registry")
        return {"path": str(out), "phase": phase}
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Registry observe failed")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


# ── Schema-driven UI ─────────────────────────────────────────


@app.get("/actions/schema")
async def actions_schema() -> dict[str, Any]:
    """
    Zwraca pełny schemat formularzy dla wszystkich akcji.
    Frontend generuje UI dynamicznie z tego schematu.
    """
    schemas = {}
    for action_name in sorted(known_action_names()):
        form = get_action_form(action_name)
        if form:
            schemas[action_name] = form.model_dump()
    return schemas


@app.get("/actions/schema/{action}", response_model=ActionFormSchema)
async def action_schema(action: str) -> ActionFormSchema:
    """Zwraca schemat formularza dla konkretnej akcji."""
    form = get_action_form(action)
    if not form:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Action '{action}' not found")
    return form


# ── Settings API ─────────────────────────────────────────────


@app.get("/settings")
async def get_settings() -> dict[str, Any]:
    """Pokaż wszystkie ustawienia systemu."""
    return {
        "settings": settings_manager.get_all(),
        "schema": settings_manager.describe(),
    }


@app.get("/settings/{section}")
async def get_settings_section(section: str) -> dict[str, Any]:
    """Pokaż ustawienia sekcji (llm, nlp, worker, file_access)."""
    data = settings_manager.get_section(section)
    if not data:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Section '{section}' not found")
    return {"section": section, "settings": data}


@app.put("/settings/{section}")
async def update_settings_section(section: str, body: dict) -> dict[str, Any]:
    """Zaktualizuj ustawienia sekcji."""
    try:
        return settings_manager.update_section(section, body)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@app.put("/settings")
async def set_setting(body: dict) -> dict[str, Any]:
    """Zmień pojedyncze ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}"""
    path = body.get("path", "")
    value = body.get("value")
    if not path:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Field 'path' is required")
    try:
        return settings_manager.set(path, value)
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@app.post("/settings/reset")
async def reset_settings(body: dict = {}) -> dict[str, Any]:
    """Resetuj ustawienia. Body: {"section": "llm"} lub {} dla wszystkich."""
    section = body.get("section")
    return settings_manager.reset(section)


# ── System Execution API ─────────────────────────────────────


@app.post("/system/execute")
async def system_execute(body: dict) -> dict[str, Any]:
    """
    Wykonaj akcję systemową bezpośrednio.
    Body: {"action": "system_file_list", "config": {"directory": "."}}
    """
    action = body.get("action", "")
    config = body.get("config", {})

    if action not in SYSTEM_EXECUTORS:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Unknown system action: '{action}'. Available: {list(SYSTEM_EXECUTORS.keys())}",
        )

    return await execute_system_action(action, config)


# ── Code Generation API ───────────────────────────────────────


@app.post("/code/generate")
async def generate_code(body: dict) -> dict[str, Any]:
    """
    Generuje kod w wybranym języku programowania.

    Body: {
        "description": "Opis kodu do wygenerowania",
        "language": "python|javascript|java|cpp|go|rust|php|ruby",
        "context": "Dodatkowy kontekst (opcjonalnie)",
        "include_tests": true/false (domyślnie false)
    }
    """
    description = body.get("description", "")
    language = body.get("language", "python")
    context = body.get("context")
    include_tests = body.get("include_tests", False)

    if not description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'description' is required"
        )

    return await code_generator.generate_code(
        description=description,
        language=language,
        context=context,
        include_tests=include_tests
    )



@app.get("/code/languages")
async def get_supported_languages() -> dict[str, Any]:
    """Zwraca listę obsługiwanych języków programowania."""
    return {
        "languages": code_generator.get_supported_languages(),
        "info": {lang: code_generator.get_language_info(lang)
                for lang in code_generator.get_supported_languages()}
    }


# ── Internal ──────────────────────────────────────────────────


async def _run_parser(req: NLPRequest) -> NLPResult:
    """Execute parser according to mode."""
    from app.routing.parser.resolve_mode import parse_with_mode

    if req.mode == "llm" and _detect_provider() == "none":
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="No LLM provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_URL.",
        )
    return await parse_with_mode(req.text, req.mode)


# ── WebSocket Voice Chat ───────────────────────────────────────


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str) -> None:
    """
    WebSocket endpoint dla voice chat w czasie rzeczywistym.

    Flow:
    1. Klient łączy się przez WebSocket
    2. Wysyła audio chunks (binary)
    3. Server streamuje do Deepgram (STT)
    4. Transkrypcja → NLP → DSL
    5. Opcjonalnie: TTS response → audio blob

    Example:
        const ws = new WebSocket('ws://localhost:8002/ws/chat/demo');
        navigator.mediaDevices.getUserMedia({audio: true}).then(stream => {
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => ws.send(e.data);
            mediaRecorder.start(250);  // 250ms chunks
        });
    """
    await websocket.accept()
    log.info("WebSocket connected: %s", conversation_id)

    streaming_stt = None
    transcript_buffer = []

    try:
        # Initialize streaming STT if available
        if is_stt_available():
            streaming_stt = StreamingSTT(language="pl")
            await streaming_stt.start()
            log.info("Streaming STT started for conversation: %s", conversation_id)

        while True:
            # Receive audio data
            data = await websocket.receive_bytes()

            if streaming_stt:
                # Stream to Deepgram
                await streaming_stt.send_audio(data)

                # Get transcript
                transcript = await streaming_stt.get_transcript()
                if transcript and transcript not in transcript_buffer:
                    transcript_buffer.append(transcript)
                    log.info("Transcript: %s", transcript)

                    # Process with NLP
                    response = await continue_conversation(conversation_id, transcript)

                    # Send response
                    await websocket.send_json({
                        "type": "transcript",
                        "text": transcript,
                        "response": response.model_dump(),
                    })
            else:
                # Fallback: batch STT
                transcript = await stt_audio(data)
                if transcript:
                    response = await continue_conversation(conversation_id, transcript)
                    await websocket.send_json({
                        "type": "transcript",
                        "text": transcript,
                        "response": response.model_dump(),
                    })

    except WebSocketDisconnect:
        log.info("WebSocket disconnected: %s", conversation_id)
    except Exception as e:
        log.exception("WebSocket error: %s", e)
    finally:
        if streaming_stt:
            final_transcript = await streaming_stt.stop()
            log.info("Final transcript: %s", final_transcript)


@app.get("/chat", response_class=HTMLResponse)
async def chat_ui() -> HTMLResponse:
    """Serwuj chat UI z voice support."""
    import pathlib
    static_dir = pathlib.Path(__file__).parent.parent / "static"
    chat_html = static_dir / "chat.html"

    if chat_html.exists():
        return HTMLResponse(content=chat_html.read_text(), status_code=HTTPStatus.OK)
    return HTMLResponse(
        content="<html><body><h1>Chat UI not found</h1><p>Create static/chat.html</p></body></html>",
        status_code=HTTPStatus.NOT_FOUND,
    )
