"""Conversation loop endpoints — /chat/*."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.audio_parser import is_stt_available, stt_audio
from app.orchestrator import (
    continue_conversation,
    get_conversation,
    start_conversation,
)
from app.schemas import ConversationResponse

log = logging.getLogger("router.chat")
router = APIRouter(tags=["chat"])


def _parse_context_json(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


async def _resolve_chat_text(text: str, audio: UploadFile | None) -> str:
    if not audio:
        return text

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
    log.info("STT transcript: %s", transcript)
    return transcript


@router.post("/chat/start", response_model=ConversationResponse)
async def chat_start(
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
    doql_context_path: str = Form(default=""),
    context_json: str = Form(default=""),
) -> ConversationResponse:
    """Rozpocznij nową konwersację."""
    text = await _resolve_chat_text(text, audio)
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


@router.post("/chat/message", response_model=ConversationResponse)
async def chat_message(
    conversation_id: str = Form(...),
    text: str = Form(default=""),
    audio: UploadFile = File(default=None),
    context_json: str = Form(default=""),
) -> ConversationResponse:
    """Kontynuuj rozmowę — uzupełnij brakujące dane."""
    text = await _resolve_chat_text(text, audio)
    if not text.strip():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'text' or 'audio' is required",
        )

    inline = _parse_context_json(context_json)
    return await continue_conversation(conversation_id, text, context_inline=inline or None)


@router.get("/chat/{conversation_id}")
async def chat_state(conversation_id: str) -> dict[str, Any]:
    """Pobierz aktualny stan konwersacji."""
    state = await get_conversation(conversation_id)
    if not state:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Conversation not found")
    return state.model_dump()


@router.post("/chat/registry/observe")
async def chat_registry_observe(request: Request) -> dict[str, Any]:
    """Merge execution / entities into environment.doql.less (registry loop)."""
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

        if conversation_id and phase == "executed" and isinstance(execution, dict):
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
