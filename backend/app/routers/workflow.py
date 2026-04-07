"""
Workflow router — /workflow/run, /workflow/history/*, /workflow/actions, /workflow/from-text.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from app.engine import NLP_SERVICE_URL, _repo, run_workflow
from app.logging_setup import get_request_id
from app.schemas import ActionInfo, RunWorkflowRequest, Step, WorkflowResult

log = logging.getLogger("router.workflow")
router = APIRouter(prefix="/workflow", tags=["workflow"])


ACTIONS_REGISTRY: list[ActionInfo] = [
    ActionInfo(name="send_invoice",   description="Generuje i wysyła fakturę",       config_schema={"to": "str", "amount": "float", "currency": "str"}),
    ActionInfo(name="send_email",     description="Wysyła e-mail",                   config_schema={"to": "str", "subject": "str", "body": "str"}),
    ActionInfo(name="generate_report",description="Generuje raport PDF/CSV",         config_schema={"type": "str", "format": "str"}),
    ActionInfo(name="crm_update",     description="Aktualizuje rekord w CRM",        config_schema={"entity": "str", "data": "dict"}),
    ActionInfo(name="notify_slack",   description="Wysyła powiadomienie Slack",      config_schema={"channel": "str", "message": "str"}),
]


@router.get("/actions", response_model=list[ActionInfo])
async def list_actions():
    """Zwraca listę dostępnych akcji (DSL vocabulary)."""
    return ACTIONS_REGISTRY


@router.post("/run", response_model=WorkflowResult)
async def run_workflow_endpoint(req: RunWorkflowRequest):
    """Uruchamia workflow — iteruje po krokach DSL i deleguje każdy krok do workera."""
    return await run_workflow(req)


@router.get("/history")
async def get_history():
    """Zwraca historię wykonanych workflow."""
    return await _repo.list_runs()


@router.get("/history/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Zwraca szczegóły konkretnego workflow."""
    run = await _repo.get_run(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return run


@router.post("/from-text")
async def workflow_from_text(body: dict):
    """
    Pełny pipeline: tekst → NLP → DSL → (opcjonalne) wykonanie.

    Body: {"text": "...", "mode": "auto|rules|llm", "execute": true|false}
    """
    text = body.get("text", "")
    mode = body.get("mode", "auto")
    execute = body.get("execute", False)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Field 'text' is required")

    async with AsyncClient(timeout=30.0, headers={"X-Request-ID": get_request_id()}) as client:
        nlp_resp = await client.post(f"{NLP_SERVICE_URL}/nlp/to-dsl", json={"text": text, "mode": mode})

    if not nlp_resp.is_success:
        ct = nlp_resp.headers.get("content-type", "")
        raise HTTPException(
            status_code=nlp_resp.status_code,
            detail=nlp_resp.json() if ct.startswith("application/json") else nlp_resp.text,
        )

    dsl_response = nlp_resp.json()

    if dsl_response.get("status") != "complete":
        return {
            "status": "incomplete",
            "missing_fields": dsl_response.get("missing_fields", []),
            "prompt_user": dsl_response.get("prompt_user"),
            "partial_workflow": dsl_response.get("workflow"),
        }

    workflow_data = dsl_response["workflow"]

    if execute and workflow_data:
        steps = workflow_data.get("steps", [])
        req = RunWorkflowRequest(
            name=workflow_data.get("name", "nlp_generated"),
            trigger=workflow_data.get("trigger", "manual"),
            steps=[Step(action=s["action"], config=s.get("config", {})) for s in steps],
        )
        result = await run_workflow(req)
        return {"status": "executed", "dsl": workflow_data, "result": result.model_dump()}

    return {"status": "complete", "dsl": workflow_data, "message": "Workflow DSL wygenerowany. Wyślij z 'execute': true aby uruchomić."}
