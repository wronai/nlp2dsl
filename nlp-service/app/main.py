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

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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
from .store.factory import get_conversation_store
from .audio_parser import stt_audio, is_stt_available, StreamingSTT

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
    store = get_conversation_store()
    return {
        "status": "ok",
        "service": "nlp-service",
        "llm_engine": "litellm",
        "llm_provider": llm_provider if llm_provider != "none" else "disabled (rules only)",
        "llm_model": LLM_MODEL if llm_provider != "none" else None,
        "conversation_store": type(store).__name__,
        "active_conversations": await store.count(),
        "actions": list(ACTIONS_REGISTRY.keys()),
    }


# ── Conversation Loop (stanowy dialog) ───────────────────────


@app.post("/chat/start", response_model=ConversationResponse)
async def chat_start(
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
):
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
                status_code=503,
                detail="STT not available. Set DEEPGRAM_API_KEY.",
            )
        audio_bytes = await audio.read()
        transcript = await stt_audio(audio_bytes)
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="Failed to transcribe audio",
            )
        text = transcript
        log.info("STT transcript: %s", text)

    # Text input
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'text' or 'audio' is required",
        )

    return await start_conversation(text)


@app.post("/chat/message", response_model=ConversationResponse)
async def chat_message(
    conversation_id: str = Form(...),
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
):
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
                status_code=503,
                detail="STT not available. Set DEEPGRAM_API_KEY.",
            )
        audio_bytes = await audio.read()
        transcript = await stt_audio(audio_bytes)
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="Failed to transcribe audio",
            )
        text = transcript
        log.info("STT transcript: %s", text)

    # Text input
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'text' or 'audio' is required",
        )

    return await continue_conversation(conversation_id, text)


@app.get("/chat/{conversation_id}")
async def chat_state(conversation_id: str):
    """Pobierz aktualny stan konwersacji."""
    state = await get_conversation(conversation_id)
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


# ── WebSocket Voice Chat ───────────────────────────────────────


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
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
async def chat_ui():
    """Serwuj chat UI z voice support."""
    import pathlib
    static_dir = pathlib.Path(__file__).parent.parent / "static"
    chat_html = static_dir / "chat.html"
    
    if chat_html.exists():
        return HTMLResponse(content=chat_html.read_text(), status_code=200)
    else:
        return HTMLResponse(
            content="<html><body><h1>Chat UI not found</h1><p>Create static/chat.html</p></body></html>",
            status_code=404,
        )
