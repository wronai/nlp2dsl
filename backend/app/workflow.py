"""
Workflow Engine — tłumaczy deklaratywny DSL na imperatywne wykonanie.

DSL (co?) → Engine (jak?) → Worker containers (robota)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from .schemas import (
    ActionInfo,
    RunWorkflowRequest,
    Step,
    StepResult,
    StepStatus,
    WorkflowResult,
)

log = logging.getLogger("workflow-engine")
router = APIRouter(prefix="/workflow", tags=["workflow"])

WORKER_URL = os.getenv("WORKER_URL", "http://worker:8000")
NLP_SERVICE_URL = os.getenv("NLP_SERVICE_URL", "http://nlp-service:8002")

# ── In-memory store (MVP — zamień na Postgres w produkcji) ────

_history: dict[str, WorkflowResult] = {}


# ── Registry dostępnych akcji ─────────────────────────────────

ACTIONS_REGISTRY: list[ActionInfo] = [
    ActionInfo(
        name="send_invoice",
        description="Generuje i wysyła fakturę",
        config_schema={"to": "str", "amount": "float", "currency": "str"},
    ),
    ActionInfo(
        name="send_email",
        description="Wysyła e-mail",
        config_schema={"to": "str", "subject": "str", "body": "str"},
    ),
    ActionInfo(
        name="generate_report",
        description="Generuje raport PDF/CSV",
        config_schema={"type": "str", "format": "str"},
    ),
    ActionInfo(
        name="crm_update",
        description="Aktualizuje rekord w CRM",
        config_schema={"entity": "str", "data": "dict"},
    ),
    ActionInfo(
        name="notify_slack",
        description="Wysyła powiadomienie Slack",
        config_schema={"channel": "str", "message": "str"},
    ),
]


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/actions", response_model=list[ActionInfo])
async def list_actions():
    """Zwraca listę dostępnych akcji (DSL vocabulary)."""
    return ACTIONS_REGISTRY


@router.post("/run", response_model=WorkflowResult)
async def run_workflow(req: RunWorkflowRequest):
    """
    Uruchamia workflow — iteruje po krokach DSL i deleguje
    każdy krok do kontenera worker (imperatywne wykonanie).
    """
    workflow_id = uuid4().hex[:12]
    result = WorkflowResult(
        workflow_id=workflow_id,
        name=req.name,
        status=StepStatus.RUNNING,
    )

    log.info("▶ Workflow '%s' [%s] — %d steps", req.name, workflow_id, len(req.steps))

    async with AsyncClient(timeout=120.0) as client:
        for step in req.steps:
            step_result = StepResult(
                step_id=step.id,
                action=step.action,
                status=StepStatus.RUNNING,
                started_at=datetime.utcnow(),
            )

            try:
                payload = {
                    "step_id": step.id,
                    "action": step.action,
                    "config": step.config,
                }
                resp = await client.post(f"{WORKER_URL}/execute", json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    step_result.status = StepStatus.COMPLETED
                    step_result.result = data.get("result")
                else:
                    step_result.status = StepStatus.FAILED
                    step_result.error = resp.text
                    log.error("✗ Step %s failed: %s", step.id, resp.text)

            except Exception as exc:
                step_result.status = StepStatus.FAILED
                step_result.error = str(exc)
                log.exception("✗ Step %s exception", step.id)

            step_result.finished_at = datetime.utcnow()
            result.steps.append(step_result)

            # fail-fast: jeśli krok padł, przerwij workflow
            if step_result.status == StepStatus.FAILED:
                result.status = StepStatus.FAILED
                _history[workflow_id] = result
                raise HTTPException(
                    status_code=400,
                    detail={
                        "workflow_id": workflow_id,
                        "failed_step": step.id,
                        "error": step_result.error,
                    },
                )

    result.status = StepStatus.COMPLETED
    _history[workflow_id] = result
    log.info("✔ Workflow '%s' [%s] completed", req.name, workflow_id)
    return result


@router.get("/history", response_model=list[WorkflowResult])
async def get_history():
    """Zwraca historię wykonanych workflow."""
    return list(_history.values())


@router.get("/history/{workflow_id}", response_model=WorkflowResult)
async def get_workflow(workflow_id: str):
    """Zwraca szczegóły konkretnego workflow."""
    wf = _history.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


# ── NLP Integration ──────────────────────────────────────────


@router.post("/from-text")
async def workflow_from_text(body: dict):
    """
    Pełny pipeline: tekst → NLP → DSL → wykonanie.

    Użytkownik mówi np.:
      "Wyślij fakturę na 1500 PLN do klient@firma.pl i powiadom na Slacku"

    System:
      1. NLP-service → intent + entities
      2. Mapper → DSL workflow
      3. Engine → wykonanie w kontenerach

    Body: {"text": "...", "mode": "auto|rules|llm", "execute": true|false}
    """
    text = body.get("text", "")
    mode = body.get("mode", "auto")
    execute = body.get("execute", False)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Field 'text' is required")

    # 1. Call NLP service
    async with AsyncClient(timeout=30.0) as client:
        nlp_resp = await client.post(
            f"{NLP_SERVICE_URL}/nlp/to-dsl",
            json={"text": text, "mode": mode},
        )

    if nlp_resp.status_code != 200:
        raise HTTPException(
            status_code=nlp_resp.status_code,
            detail=nlp_resp.json() if nlp_resp.headers.get("content-type", "").startswith("application/json") else nlp_resp.text,
        )

    dsl_response = nlp_resp.json()

    # 2. Check if complete
    if dsl_response.get("status") != "complete":
        return {
            "status": "incomplete",
            "missing_fields": dsl_response.get("missing_fields", []),
            "prompt_user": dsl_response.get("prompt_user"),
            "partial_workflow": dsl_response.get("workflow"),
        }

    workflow_data = dsl_response["workflow"]

    # 3. Optionally execute
    if execute and workflow_data:
        steps = workflow_data.get("steps", [])
        req = RunWorkflowRequest(
            name=workflow_data.get("name", "nlp_generated"),
            trigger=workflow_data.get("trigger", "manual"),
            steps=[
                Step(action=s["action"], config=s.get("config", {}))
                for s in steps
            ],
        )
        result = await run_workflow(req)
        return {
            "status": "executed",
            "dsl": workflow_data,
            "result": result.model_dump(),
        }

    return {
        "status": "complete",
        "dsl": workflow_data,
        "message": "Workflow DSL wygenerowany. Wyślij z 'execute': true aby uruchomić.",
    }


# ── Chat (Conversation Loop) ─────────────────────────────────


@router.post("/chat/start")
async def chat_start(body: dict):
    """
    Rozpocznij konwersację AI → DSL.

    System prowadzi dialog, dopytuje o brakujące dane,
    i generuje dynamiczny formularz UI.

    Body: {"text": "Wyślij fakturę na 1500 PLN"}
    """
    async with AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/chat/start", json=body)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/chat/message")
async def chat_message(body: dict):
    """
    Kontynuuj konwersację — uzupełnij brakujące dane.

    Body: {"conversation_id": "abc", "text": "klient@firma.pl"}
    """
    async with AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/chat/message", json=body)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    result = resp.json()

    # Auto-execute if ready and user said "uruchom"
    text_lower = body.get("text", "").lower()
    execute_keywords = ["uruchom", "wykonaj", "start", "run", "ok", "tak", "go"]

    if result.get("status") == "ready" and any(kw in text_lower for kw in execute_keywords):
        dsl = result.get("dsl")
        if dsl:
            steps = dsl.get("steps", [])
            req = RunWorkflowRequest(
                name=dsl.get("name", "chat_generated"),
                trigger=dsl.get("trigger", "manual"),
                steps=[
                    Step(action=s["action"], config=s.get("config", {}))
                    for s in steps
                ],
            )
            wf_result = await run_workflow(req)
            result["status"] = "executed"
            result["execution"] = wf_result.model_dump()

    return result


@router.get("/chat/{conversation_id}")
async def chat_get_state(conversation_id: str):
    """Pobierz stan konwersacji."""
    async with AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/chat/{conversation_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── Schema-driven UI ─────────────────────────────────────────


@router.get("/actions/schema")
async def actions_schema():
    """Schematy formularzy UI — frontend generuje dynamicznie."""
    async with AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/actions/schema")
    return resp.json()


@router.get("/actions/schema/{action}")
async def action_schema(action: str):
    """Schemat formularza dla konkretnej akcji."""
    async with AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/actions/schema/{action}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
