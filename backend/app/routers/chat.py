"""
Chat router — /workflow/chat/start, /workflow/chat/message, /workflow/chat/{id}.

Proxy do nlp-service z opcjonalnym auto-execute przy "uruchom".
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from httpx import AsyncClient, Response

from app.engine import NLP_SERVICE_URL, run_workflow
from app.logging_setup import get_request_id
from app.schemas import RunWorkflowRequest, Step

log = logging.getLogger("router.chat")
router = APIRouter(prefix="/workflow", tags=["chat"])

_PROXY_TIMEOUT_SECONDS: float = float("30.0")


async def _proxy_chat_payload(request: Request, endpoint: str) -> tuple[Response, dict[str, Any]]:
    """Forward JSON or form-data payloads to the NLP service chat endpoints."""
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = {}
        files = {}

        for key, value in form.multi_items():
            if hasattr(value, "filename") and hasattr(value, "read"):
                files[key] = (
                    value.filename,
                    await value.read(),
                    getattr(value, "content_type", None) or "application/octet-stream",
                )
            else:
                data[key] = value

        async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS, headers={"X-Request-ID": get_request_id()}) as client:
            resp = await client.post(f"{NLP_SERVICE_URL}{endpoint}", data=data, files=files or None)
        return resp, data

    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}{endpoint}", data=body)
    return resp, body


@router.post("/chat/start")
async def chat_start(request: Request) -> dict[str, Any]:
    """
    Rozpocznij konwersację AI → DSL.

    Body: {"text": "Wyślij fakturę na 1500 PLN"}
    """
    resp, _ = await _proxy_chat_payload(request, "/chat/start")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/chat/message")
async def chat_message(request: Request) -> dict[str, Any]:
    """
    Kontynuuj konwersację — uzupełnij brakujące dane.

    Body: {"conversation_id": "abc", "text": "klient@firma.pl"}
    """
    resp, body = await _proxy_chat_payload(request, "/chat/message")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    result = resp.json()

    text_lower = body.get("text", "").lower()
    execute_keywords = ["uruchom", "wykonaj", "start", "run", "ok", "tak", "go"]

    if result.get("status") == "ready" and any(kw in text_lower for kw in execute_keywords):
        dsl = result.get("dsl")
        if dsl:
            steps = dsl.get("steps", [])
            req = RunWorkflowRequest(
                name=dsl.get("name", "chat_generated"),
                trigger=dsl.get("trigger", "manual"),
                steps=[Step(action=s["action"], config=s.get("config", {})) for s in steps],
            )
            wf_result = await run_workflow(req)
            result["status"] = "executed"
            result["execution"] = wf_result.model_dump()

    return result


@router.get("/chat/{conversation_id}")
async def chat_get_state(conversation_id: str) -> dict[str, Any]:
    """Pobierz stan konwersacji."""
    async with AsyncClient(timeout=float("10.0"), headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/chat/{conversation_id}")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
