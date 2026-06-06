"""
Workflow router — /workflow/run, /workflow/history/*, /workflow/actions, /workflow/from-text.
"""

import asyncio
import json
import logging
import os
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from httpx import AsyncClient
from starlette.responses import StreamingResponse

from app.engine import NLP_SERVICE_URL, _repo, run_workflow, start_workflow
from app.action_catalog import fetch_action_catalog
from app.dsl_validation import dsl_validation_response, validate_dsl_for_execution
from app.idempotency import idempotency_store
from app.workflow_execute import resolve_idempotency_key, run_idempotent_workflow
from app.logging_setup import get_request_id
from app.workflow_events import TERMINAL_EVENT_TYPES, workflow_event_hub
from app.execution_policy import policy_blocked_response, validate_workflow_execution_policy
from app.workflow_lifecycle import (
    attach_validation_to_plan,
    validation_report_for_workflow,
    workflow_from_lifecycle_body,
    workflow_validation_payload,
)
from nlp2dsl_sdk.workflow.events import workflow_snapshot_from_events
from nlp2dsl_sdk.workflow.simulate import simulate_workflow_payload
from app.schemas import ActionInfo, RunWorkflowRequest, WorkflowResult

log = logging.getLogger("router.workflow")
router = APIRouter(prefix="/workflow", tags=["workflow"])

_PROXY_TIMEOUT_SECONDS: float = float("30.0")


def _format_sse(event: str, data: dict[str, Any], *, event_id: str | None = None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    lines: list[str] = []

    if event_id:
        lines.append(f"id: {event_id}")
    if event:
        lines.append(f"event: {event}")
    for line in payload.splitlines() or [payload]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


def _workflow_snapshot(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": run.get("workflow_id"),
        "name": run.get("name"),
        "status": run.get("status"),
        "trigger": run.get("trigger"),
        "steps": run.get("steps", []),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
    }



@router.post("/nlp/orient")
async def orient_nlp(body: dict[str, Any]) -> dict[str, Any]:
    """Proxy orientacji zapytania do nlp-service (Mullm ingress)."""
    async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/nlp/orient", json=body)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.get("/actions", response_model=list[ActionInfo])
async def list_actions() -> list[ActionInfo]:
    """Zwraca listę dostępnych akcji — proxy do nlp-service /nlp/actions (C1)."""
    try:
        async with AsyncClient(
            timeout=_PROXY_TIMEOUT_SECONDS,
            headers={"X-Request-ID": get_request_id()},
        ) as client:
            return await fetch_action_catalog(NLP_SERVICE_URL, client=client)
    except Exception as exc:
        log.exception("Failed to fetch action catalog from nlp-service")
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f"Could not load action catalog from nlp-service: {exc}",
        ) from exc


@router.post("/run", response_model=WorkflowResult)
async def run_workflow_endpoint(req: RunWorkflowRequest) -> WorkflowResult:
    """Uruchamia workflow — iteruje po krokach DSL i deleguje każdy krok do workera."""
    return await run_workflow(req)


@router.post("/start", response_model=WorkflowResult)
async def start_workflow_endpoint(req: RunWorkflowRequest) -> WorkflowResult:
    """Startuje workflow w tle i zwraca natychmiastowy snapshot running."""
    return await start_workflow(req)


@router.get("/history")
async def get_history() -> list[dict]:
    """Zwraca historię wykonanych workflow."""
    return await _repo.list_runs()


@router.get("/history/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict[str, Any]:
    """Zwraca szczegóły konkretnego workflow."""
    run = await _repo.get_run(workflow_id)
    if not run:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Workflow not found")
    return run


@router.get("/history/{workflow_id}/events")
async def get_workflow_events(workflow_id: str, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    """Return persisted lifecycle events and a reconstructed status snapshot."""
    run = await _repo.get_run(workflow_id)
    if not run:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Workflow not found")

    events = await _repo.list_events(workflow_id, limit=limit, offset=offset)
    reconstructed = workflow_snapshot_from_events(events)
    return {
        "workflow_id": workflow_id,
        "run": _workflow_snapshot(run),
        "events": events,
        "reconstructed": reconstructed,
        "count": len(events),
    }


@router.get("/stream/{workflow_id}")
async def stream_workflow(workflow_id: str, request: Request) -> StreamingResponse:
    """SSE stream with live workflow lifecycle events."""
    run = await _repo.get_run(workflow_id)
    if not run:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Workflow not found")

    async def event_generator():
        snapshot = _workflow_snapshot(run)
        yield _format_sse("snapshot", snapshot, event_id=f"{workflow_id}:snapshot")

        if snapshot.get("status") in {"completed", "failed"}:
            terminal_event = "workflow_completed" if snapshot.get("status") == "completed" else "workflow_failed"
            yield _format_sse(terminal_event, snapshot, event_id=f"{workflow_id}:{terminal_event}")
            return

        queue = await workflow_event_hub.subscribe(workflow_id)
        try:
            current = await _repo.get_run(workflow_id)
            if current:
                snapshot = _workflow_snapshot(current)
                if snapshot.get("status") in {"completed", "failed"}:
                    terminal_event = "workflow_completed" if snapshot.get("status") == "completed" else "workflow_failed"
                    yield _format_sse(terminal_event, snapshot, event_id=f"{workflow_id}:{terminal_event}")
                    return

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield _format_sse(event.event_type, event.to_dict(), event_id=event.event_id)
                if event.event_type in TERMINAL_EVENT_TYPES:
                    break
        finally:
            await workflow_event_hub.unsubscribe(workflow_id, queue)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


@router.get("/catalog/drift")
async def workflow_catalog_drift() -> dict[str, Any]:
    """Preflight diagnostics: nlp-service catalog vs worker handler registry."""
    from nlp2dsl_sdk.validation.contract_drift import build_catalog_drift_report

    try:
        async with AsyncClient(
            timeout=_PROXY_TIMEOUT_SECONDS,
            headers={"X-Request-ID": get_request_id()},
        ) as client:
            resp = await client.get(f"{NLP_SERVICE_URL}/nlp/actions")
        resp.raise_for_status()
        nlp_catalog = resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f"Could not load action catalog from nlp-service: {exc}",
        ) from exc

    worker_url = os.getenv("WORKER_URL", "http://worker:8004").rstrip("/")
    try:
        async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS) as client:
            wresp = await client.get(f"{worker_url}/health")
        wresp.raise_for_status()
        worker_handlers = sorted(wresp.json().get("actions", []))
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f"Could not load worker actions: {exc}",
        ) from exc

    if not isinstance(nlp_catalog, dict):
        nlp_catalog = {}

    report = build_catalog_drift_report(
        nlp_catalog=nlp_catalog,
        worker_handlers=worker_handlers,
    )
    payload = report.to_dict()
    payload["stage"] = "preflight"
    payload["status"] = "ready" if report.ok else "validation_failed"
    return payload


@router.post("/from-text")
async def workflow_from_text(body: dict) -> dict[str, Any]:
    """
    Pełny pipeline: tekst → NLP → DSL → (opcjonalne) wykonanie.

    Body: {"text": "...", "mode": "auto|rules|llm", "execute": true|false, "simulate": true|false}
    """
    text = body.get("text", "")
    mode = body.get("mode", "auto")
    execute = body.get("execute", False)
    simulate = body.get("simulate", False)

    if not text.strip():
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Field 'text' is required")

    async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS, headers={"X-Request-ID": get_request_id()}) as client:
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

    workflow_data = dsl_response.get("workflow")
    contract_issues = validate_dsl_for_execution(workflow_data)
    if contract_issues:
        return dsl_validation_response(workflow_data, contract_issues)

    if simulate and workflow_data:
        report = validation_report_for_workflow(workflow_data)
        payload = simulate_workflow_payload(workflow_data)
        payload["validation"] = report.model_dump()
        payload["dsl"] = workflow_data
        payload["can_execute"] = report.can_execute and payload.get("can_execute", False)
        if not report.can_execute:
            payload["status"] = "validation_failed"
            payload["missing_fields"] = report.missing_fields
        return payload

    if execute and workflow_data:
        idempotency_key = resolve_idempotency_key(
            explicit_key=str(body.get("idempotency_key") or "").strip() or None,
            workflow=workflow_data,
        )
        execution = await run_idempotent_workflow(
            workflow_data,
            idempotency_key=idempotency_key,
        )
        return {
            "status": "executed",
            "dsl": workflow_data,
            "result": execution["result"],
            "idempotency_key": execution.get("idempotency_key"),
            "idempotent_replay": execution.get("idempotent_replay", False),
        }

    return {"status": "complete", "dsl": workflow_data, "message": "Workflow DSL wygenerowany. Wyślij z 'execute': true aby uruchomić."}


@router.post("/plan")
async def workflow_plan(body: dict[str, Any]) -> dict[str, Any]:
    """
    Lifecycle plan endpoint: text → NLP plan → DSL validation report.

    Body: {"text": "...", "mode": "auto|rules|llm"}
    """
    text = body.get("text", "")
    mode = body.get("mode", "auto")

    if not str(text).strip():
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Field 'text' is required")

    async with AsyncClient(
        timeout=_PROXY_TIMEOUT_SECONDS,
        headers={"X-Request-ID": get_request_id()},
    ) as client:
        nlp_resp = await client.post(f"{NLP_SERVICE_URL}/nlp/plan", json={"text": text, "mode": mode})

    if not nlp_resp.is_success:
        ct = nlp_resp.headers.get("content-type", "")
        raise HTTPException(
            status_code=nlp_resp.status_code,
            detail=nlp_resp.json() if ct.startswith("application/json") else nlp_resp.text,
        )

    plan = nlp_resp.json()
    return attach_validation_to_plan(plan)


@router.post("/validate")
async def workflow_validate(body: dict[str, Any]) -> dict[str, Any]:
    """
    Validate workflow DSL without execution.

    Body: {"workflow": {...}} or {"dsl": {...}}, optional `"check_policy": true`.
    """
    workflow_data = workflow_from_lifecycle_body(body)
    if workflow_data is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'workflow' is required",
        )
    payload = workflow_validation_payload(workflow_data)
    if bool(body.get("check_policy", False)):
        policy_issues = await validate_workflow_execution_policy(
            workflow_data,
            body,
            executing=True,
            skip_access_check=bool(body.get("skip_access_check", False)),
        )
        if policy_issues:
            blocked = policy_blocked_response(workflow_data, policy_issues)
            payload.update(blocked)
            payload["workflow"] = workflow_data
    return payload


@router.post("/simulate")
async def workflow_simulate(body: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate workflow execution without side effects.

    Body: {"workflow": {...}} or {"dsl": {...}} or {"text": "...", "mode": "auto|rules|llm"}.
    """
    text = str(body.get("text") or "").strip()
    mode = body.get("mode", "auto")

    if text:
        async with AsyncClient(
            timeout=_PROXY_TIMEOUT_SECONDS,
            headers={"X-Request-ID": get_request_id()},
        ) as client:
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
                "stage": "simulate",
                "status": dsl_response.get("status", "incomplete"),
                "missing_fields": dsl_response.get("missing_fields", []),
                "prompt_user": dsl_response.get("prompt_user"),
                "partial_workflow": dsl_response.get("workflow"),
            }

        workflow_data = dsl_response.get("workflow")
    else:
        workflow_data = workflow_from_lifecycle_body(body)

    if workflow_data is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'workflow' or 'text' is required",
        )

    report = validation_report_for_workflow(workflow_data)
    payload = simulate_workflow_payload(workflow_data)
    payload["validation"] = report.model_dump()
    payload["can_execute"] = report.can_execute and payload.get("can_execute", False)
    if not report.can_execute:
        payload["status"] = "validation_failed"
        payload["missing_fields"] = report.missing_fields
    return payload


@router.post("/execute")
async def workflow_execute(body: dict[str, Any]) -> dict[str, Any]:
    """
    Execute validated workflow DSL.

    Body: {"workflow": {...}, "dry_run": false, "idempotency_key": "..."}.
    """
    workflow_data = workflow_from_lifecycle_body(body)
    if workflow_data is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Field 'workflow' is required",
        )

    report = validation_report_for_workflow(workflow_data)
    if not report.can_execute:
        return {
            "stage": "execute",
            "status": "validation_failed",
            "workflow": workflow_data,
            "validation": report.model_dump(),
            "missing_fields": report.missing_fields,
            "can_execute": False,
        }

    idempotency_key = resolve_idempotency_key(
        explicit_key=str(body.get("idempotency_key") or "").strip() or None,
        workflow=workflow_data,
    )

    if bool(body.get("dry_run", False)):
        return {
            "stage": "execute",
            "status": "ready",
            "workflow": workflow_data,
            "validation": report.model_dump(),
            "dry_run": True,
            "can_execute": True,
            "idempotency_key": idempotency_key,
        }

    if not bool(body.get("skip_policy_check", False)):
        policy_issues = await validate_workflow_execution_policy(
            workflow_data,
            body,
            executing=True,
            skip_access_check=bool(body.get("skip_access_check", False)),
        )
        if policy_issues:
            blocked = policy_blocked_response(workflow_data, policy_issues)
            blocked["stage"] = "execute"
            blocked["workflow"] = workflow_data
            blocked["validation"] = report.model_dump()
            return blocked

    execution = await run_idempotent_workflow(
        workflow_data,
        idempotency_key=idempotency_key,
    )
    return {
        "stage": "execute",
        "status": "executed",
        "workflow": workflow_data,
        "validation": report.model_dump(),
        "result": execution["result"],
        "idempotency_key": execution.get("idempotency_key"),
        "idempotent_replay": execution.get("idempotent_replay", False),
    }


@router.post("/idempotency/clear")
async def clear_idempotency_store() -> dict[str, str]:
    """Dev/CI helper — drop cached idempotency records before example runs."""
    await idempotency_store.clear()
    return {"status": "cleared"}
