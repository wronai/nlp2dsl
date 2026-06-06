"""
Chat router — /workflow/chat/start, /workflow/chat/message, /workflow/chat/{id}.

Proxy do nlp-service z opcjonalnym auto-execute przy "uruchom".
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from httpx import AsyncClient, Response

from app.engine import NLP_SERVICE_URL, run_workflow
from app.attachment_validation import ensure_attachment_validation
from app.dsl_validation import dsl_validation_response, validate_dsl_for_execution
from app.logging_setup import get_request_id
from app.schemas import RunWorkflowRequest, Step

log = logging.getLogger("router.chat")
router = APIRouter(prefix="/workflow", tags=["chat"])

_PROXY_TIMEOUT_SECONDS: float = float("30.0")
_EXECUTE_KEYWORDS: tuple[str, ...] = ("uruchom", "wykonaj", "start", "run", "ok", "tak", "go")


def _merge_attachment_validation(result: dict[str, Any]) -> None:
    """Promote attachment_validation from execution step result to top-level response."""
    if result.get("attachment_validation"):
        return
    execution = result.get("execution") or {}
    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_result = step.get("result") or {}
        if isinstance(step_result, dict) and step_result.get("attachment_validation"):
            result["attachment_validation"] = step_result["attachment_validation"]
            return


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
    if result.get("status") != "ready" or not _execution_requested(result, body):
        return result
    return await _execute_ready_dsl(result, body)


def _execution_requested(result: dict[str, Any], body: dict[str, Any]) -> bool:
    return _is_explicit_execute_request(body) or _is_auto_execute_requested(result, body)


def _is_explicit_execute_request(body: dict[str, Any]) -> bool:
    text_lower = str(body.get("text", "")).lower()
    return any(keyword in text_lower for keyword in _EXECUTE_KEYWORDS)


def _is_auto_execute_requested(result: dict[str, Any], body: dict[str, Any]) -> bool:
    return bool(
        result.get("auto_execute")
        or body.get("sync_auto_execute")
        or body.get("auto_execute")
    )


def _dsl_steps(dsl: dict[str, Any]) -> list[dict[str, Any]]:
    steps = dsl.get("steps") or []
    return [step for step in steps if isinstance(step, dict)]


def _mullm_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [step for step in steps if str(step.get("action", "")).startswith("mullm_")]


def _uses_mullm_backend(result: dict[str, Any], steps: list[dict[str, Any]]) -> bool:
    return bool(_mullm_steps(steps) or result.get("execution_backend") == "mullm")


def _prepare_mullm_execution(result: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    mullm_only_steps = _mullm_steps(steps)
    result["status"] = "ready"
    result["execution_backend"] = "mullm"
    result["execution"] = {
        "backend": "mullm",
        "steps": mullm_only_steps or steps,
        "hint": "Wykonaj w Mullm workspace (conductor / BFF).",
    }
    return result


def _workflow_request_from_dsl(dsl: dict[str, Any], steps: list[dict[str, Any]]) -> RunWorkflowRequest:
    return RunWorkflowRequest(
        name=dsl.get("name", "chat_generated"),
        trigger=dsl.get("trigger", "manual"),
        steps=[Step(action=step["action"], config=step.get("config", {})) for step in steps],
    )


def _mark_auto_execute_message(result: dict[str, Any], body: dict[str, Any]) -> None:
    if not _is_auto_execute_requested(result, body) or _is_explicit_execute_request(body):
        return

    ready_msg = str(result.get("message") or "")
    executed_msg = "Wykonano automatycznie (sync_auto_execute)."
    if "Wyślij 'uruchom'" in ready_msg:
        result["message"] = ready_msg.replace(
            "Wyślij 'uruchom' aby wykonać.",
            executed_msg,
        ).replace(
            "Wyślij 'uruchom' aby wykonać",
            executed_msg.rstrip("."),
        )
    elif "automatycznie" not in ready_msg.lower():
        result["message"] = f"{ready_msg}\n{executed_msg}".strip()


def _doql_context_path(body: dict[str, Any]) -> Any:
    return body.get("doql_context_path") or body.get("doqlContextPath")


def _execution_observation_from_dsl(dsl: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    entities: dict[str, Any] = {}
    intent: str | None = None
    for step in _dsl_steps(dsl):
        intent = intent or step.get("action")
        entities.update(step.get("config") or {})
    return intent, entities


async def _observe_registry_execution(result: dict[str, Any], body: dict[str, Any]) -> None:
    doql_path = _doql_context_path(body)
    if not doql_path:
        return

    dsl = result.get("dsl") or {}
    if not isinstance(dsl, dict):
        dsl = {}
    intent, entities = _execution_observation_from_dsl(dsl)
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


async def _execute_ready_dsl(result: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    dsl = result.get("dsl")
    if not isinstance(dsl, dict) or not dsl:
        return result

    contract_issues = validate_dsl_for_execution(dsl)
    if contract_issues:
        result.update(dsl_validation_response(dsl, contract_issues))
        result["execution_backend"] = None
        result.pop("execution", None)
        return result

    steps = _dsl_steps(dsl)
    if _uses_mullm_backend(result, steps):
        return _prepare_mullm_execution(result, steps)

    req = _workflow_request_from_dsl(dsl, steps)
    wf_result = await run_workflow(req)
    result["status"] = "executed"
    result["execution"] = wf_result.model_dump()
    result["execution_backend"] = "worker"
    _merge_attachment_validation(result)
    ensure_attachment_validation(result)
    _mark_auto_execute_message(result, body)
    await _observe_registry_execution(result, body)
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
