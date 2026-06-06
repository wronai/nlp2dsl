"""WebSocket voice chat and chat UI."""

from __future__ import annotations

import logging
import pathlib
from http import HTTPStatus

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.audio_parser import StreamingSTT, is_stt_available, stt_audio
from app.orchestrator import continue_conversation

log = logging.getLogger("router.ws")
router = APIRouter(tags=["ws"])


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str) -> None:
    """WebSocket endpoint dla voice chat w czasie rzeczywistym."""
    await websocket.accept()
    log.info("WebSocket connected: %s", conversation_id)

    streaming_stt = None
    transcript_buffer: list[str] = []

    try:
        if is_stt_available():
            streaming_stt = StreamingSTT(language="pl")
            await streaming_stt.start()
            log.info("Streaming STT started for conversation: %s", conversation_id)

        while True:
            data = await websocket.receive_bytes()

            if streaming_stt:
                await streaming_stt.send_audio(data)
                transcript = await streaming_stt.get_transcript()
                if transcript and transcript not in transcript_buffer:
                    transcript_buffer.append(transcript)
                    log.info("Transcript: %s", transcript)
                    response = await continue_conversation(conversation_id, transcript)
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "text": transcript,
                            "response": response.model_dump(),
                        }
                    )
            else:
                transcript = await stt_audio(data)
                if transcript:
                    response = await continue_conversation(conversation_id, transcript)
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "text": transcript,
                            "response": response.model_dump(),
                        }
                    )

    except WebSocketDisconnect:
        log.info("WebSocket disconnected: %s", conversation_id)
    except Exception:
        log.exception("WebSocket error")
    finally:
        if streaming_stt:
            final_transcript = await streaming_stt.stop()
            log.info("Final transcript: %s", final_transcript)


@router.get("/chat", response_class=HTMLResponse)
async def chat_ui() -> HTMLResponse:
    """Serwuj chat UI z voice support."""
    static_dir = pathlib.Path(__file__).resolve().parents[2] / "static"
    chat_html = static_dir / "chat.html"

    if chat_html.exists():
        return HTMLResponse(content=chat_html.read_text(), status_code=HTTPStatus.OK)
    return HTMLResponse(
        content="<html><body><h1>Chat UI not found</h1><p>Create static/chat.html</p></body></html>",
        status_code=HTTPStatus.NOT_FOUND,
    )
