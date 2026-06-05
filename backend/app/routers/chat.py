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


async def _maybe_auto_execute(result: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Run workflow when status=ready and sync_auto_execute or explicit execute keyword."""
    text_lower = str(body.get("text", "")).lower()
    execute_keywords = ["uruchom", "wykonaj", "start", "run", "ok", "tak", "go"]
    explicit_execute = any(kw in text_lower for kw in execute_keywords)
    auto_flag = bool(
        result.get("auto_execute")
        or body.get("sync_auto_execute")
        or body.get("auto_execute")
    )
    if result.get("status") != "ready" or not (explicit_execute or auto_flag):
        return result
    return await _execute_ready_dsl(result, body)


async def _execute_ready_dsl(result: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    dsl = result.get("dsl")
    if not dsl:
        return result
    steps = dsl.get("steps", [])
    mullm_steps = [s for s in steps if str(s.get("action", "")).startswith("mullm_")]
    if mullm_steps or result.get("execution_backend") == "mullm":
        result["status"] = "ready"
        result["execution_backend"] = "mullm"
        result["execution"] = {
            "backend": "mullm",
            "steps": mullm_steps or steps,
            "hint": "Wykonaj w Mullm workspace (conductor / BFF).",
        }
        return result

    req = RunWorkflowRequest(
        name=dsl.get("name", "chat_generated"),
        trigger=dsl.get("trigger", "manual"),
        steps=[Step(action=s["action"], config=s.get("config", {})) for s in steps],
    )
    wf_result = await run_workflow(req)
    result["status"] = "executed"
    result["execution"] = wf_result.model_dump()
    result["execution_backend"] = "worker"

    doql_path = body.get("doql_context_path") or body.get("doqlContextPath")
    if doql_path:
        dsl = result.get("dsl") or {}
        entities: dict[str, Any] = {}
        intent: str | None = None
        for step in dsl.get("steps") or []:
            if isinstance(step, dict):
                intent = intent or step.get("action")
                entities.update(step.get("config") or {})
        try:
            async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS) as observe_client:
                await observe_client.post(
                    f"{NLP_SERVICE_URL}/chat/registry/observe",
                    json={
                        "doql_context_path": doql_path,
                        "conversation_id": result.get("conversation_id"),
                        "phase": "executed",
                        "execution": result.get("execution"),
                        "intent": intent,
                        "entities": entities,
                    },
                )
        except Exception:
            log.debug("Registry observe after execute skipped", exc_info=True)
    return result


@router.post("/chat/start")
async def chat_start(request: Request) -> dict[str, Any]:
    """
    Rozpocznij konwersację AI → DSL.

    Body: {"text": "Wyślij fakturę na 1500 PLN"}
    """
    resp, body = await _proxy_chat_payload(request, "/chat/start")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    result = resp.json()
    return await _maybe_auto_execute(result, body)


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
    return await _maybe_auto_execute(result, body)


@router.get("/chat/{conversation_id}")
async def chat_get_state(conversation_id: str) -> dict[str, Any]:
    """Pobierz stan konwersacji."""
    async with AsyncClient(timeout=float("10.0"), headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/chat/{conversation_id}")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
