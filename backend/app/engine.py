"""
Workflow Engine — tłumaczy deklaratywny DSL na imperatywne wykonanie.

Współdzielony moduł: run_workflow() + _repo singleton używany przez wszystkie routery.
"""

import asyncio
import logging
from http import HTTPStatus
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from httpx import AsyncClient

from app.config import settings
from app.db import create_workflow_repo
from app.logging_setup import get_request_id
from app.workflow_events import WorkflowEvent, workflow_event_hub
from app.schemas import (
    RunWorkflowRequest,
    StepResult,
    StepStatus,
    WorkflowResult,
)

log = logging.getLogger("workflow-engine")

WORKER_URL = settings.worker_url
NLP_SERVICE_URL = settings.nlp_service_url
WORKFLOW_ID_LENGTH: int = int("12")
WORKFLOW_TIMEOUT_SECONDS: float = float("120.0")

_repo = create_workflow_repo()
_background_workflow_tasks: set[asyncio.Task] = set()


def _workflow_steps_payload(result: WorkflowResult) -> list[dict]:
    return [step.model_dump(mode="json") for step in result.steps]


async def _persist_workflow_snapshot(req: RunWorkflowRequest, result: WorkflowResult) -> None:
    await _repo.save_run(
        workflow_id=result.workflow_id,
        name=req.name,
        status=result.status.value,
        data={
            "trigger": req.trigger or "manual",
            "steps": _workflow_steps_payload(result),
        },
    )


async def _publish_workflow_event(
    workflow_id: str,
    event_type: str,
    status: str,
    message: str,
    *,
    step_id: str | None = None,
    action: str | None = None,
    step_index: int | None = None,
    total_steps: int | None = None,
    payload: dict | None = None,
) -> None:
    await workflow_event_hub.publish(
        WorkflowEvent(
            workflow_id=workflow_id,
            event_type=event_type,
            status=status,
            message=message,
            step_id=step_id,
            action=action,
            step_index=step_index,
            total_steps=total_steps,
            payload=payload or {},
        )
    )


async def _execute_workflow(
    req: RunWorkflowRequest,
    workflow_id: str,
    *,
    raise_on_failure: bool,
    persist_initial: bool,
) -> WorkflowResult:
    result = WorkflowResult(
        workflow_id=workflow_id,
        name=req.name,
        status=StepStatus.RUNNING,
    )

    log.info("▶ Workflow '%s' [%s] — %d steps", req.name, workflow_id, len(req.steps))

    if persist_initial:
        await _persist_workflow_snapshot(req, result)

    await _publish_workflow_event(
        workflow_id,
        "workflow_started",
        StepStatus.RUNNING.value,
        f"Workflow '{req.name}' wystartował",
        total_steps=len(req.steps),
        payload={
            "name": req.name,
            "trigger": req.trigger or "manual",
            "steps": len(req.steps),
        },
    )

    trace_headers = {"X-Request-ID": get_request_id()}

    try:
        async with AsyncClient(timeout=WORKFLOW_TIMEOUT_SECONDS, headers=trace_headers) as client:
            total_steps = len(req.steps)
            for step_index, step in enumerate(req.steps, start=1):
                step_result = StepResult(
                    step_id=step.id,
                    action=step.action,
                    status=StepStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                result.steps.append(step_result)

                await _publish_workflow_event(
                    workflow_id,
                    "step_started",
                    StepStatus.RUNNING.value,
                    f"Krok {step_index}/{total_steps} uruchomiony: {step.action}",
                    step_id=step.id,
                    action=step.action,
                    step_index=step_index,
                    total_steps=total_steps,
                    payload={"config": step.config},
                )
                await _persist_workflow_snapshot(req, result)

                try:
                    payload = {"step_id": step.id, "action": step.action, "config": step.config}
                    resp = await client.post(f"{WORKER_URL}/execute", json=payload)

                    if resp.is_success:
                        step_result.status = StepStatus.COMPLETED
                        step_result.result = resp.json().get("result")
                    else:
                        step_result.status = StepStatus.FAILED
                        step_result.error = resp.text
                        log.error("✗ Step %s failed: %s", step.id, resp.text)

                except Exception as exc:
                    step_result.status = StepStatus.FAILED
                    step_result.error = str(exc)
                    log.exception("✗ Step %s exception", step.id)

                step_result.finished_at = datetime.now(UTC)

                if step_result.status == StepStatus.COMPLETED:
                    await _publish_workflow_event(
                        workflow_id,
                        "step_completed",
                        StepStatus.RUNNING.value,
                        f"Krok {step_index}/{total_steps} zakończony: {step.action}",
                        step_id=step.id,
                        action=step.action,
                        step_index=step_index,
                        total_steps=total_steps,
                        payload={"result": step_result.result},
                    )
                    await _persist_workflow_snapshot(req, result)
                    continue

                result.status = StepStatus.FAILED
                await _persist_workflow_snapshot(req, result)
                await _publish_workflow_event(
                    workflow_id,
                    "step_failed",
                    StepStatus.FAILED.value,
                    f"Krok {step_index}/{total_steps} nie powiódł się: {step.action}",
                    step_id=step.id,
                    action=step.action,
                    step_index=step_index,
                    total_steps=total_steps,
                    payload={"error": step_result.error},
                )
                await _publish_workflow_event(
                    workflow_id,
                    "workflow_failed",
                    StepStatus.FAILED.value,
                    f"Workflow '{req.name}' zakończył się błędem",
                    total_steps=len(req.steps),
                    payload={"error": step_result.error, "failed_step": step.id},
                )
                if raise_on_failure:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail={"workflow_id": workflow_id, "failed_step": step.id, "error": step_result.error},
                    )
                return result

        result.status = StepStatus.COMPLETED
        await _persist_workflow_snapshot(req, result)
        await _publish_workflow_event(
            workflow_id,
            "workflow_completed",
            StepStatus.COMPLETED.value,
            f"Workflow '{req.name}' został zakończony",
            total_steps=len(req.steps),
            payload={"steps": _workflow_steps_payload(result)},
        )
        log.info("✔ Workflow '%s' [%s] completed", req.name, workflow_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        result.status = StepStatus.FAILED
        await _persist_workflow_snapshot(req, result)
        await _publish_workflow_event(
            workflow_id,
            "workflow_failed",
            StepStatus.FAILED.value,
            f"Workflow '{req.name}' zakończył się błędem",
            total_steps=len(req.steps),
            payload={"error": str(exc)},
        )
        log.exception("✗ Workflow '%s' [%s] crashed", req.name, workflow_id)
        if raise_on_failure:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail={"workflow_id": workflow_id, "error": str(exc)},
            )
        return result


def _track_background_task(task: asyncio.Task) -> None:
    _background_workflow_tasks.add(task)

    def _cleanup(completed: asyncio.Task) -> None:
        _background_workflow_tasks.discard(completed)
        try:
            completed.result()
        except Exception:
            log.exception("Background workflow task failed")

    task.add_done_callback(_cleanup)


async def run_workflow(req: RunWorkflowRequest) -> WorkflowResult:
    """Uruchamia workflow — iteruje po krokach DSL i deleguje do workera."""
    workflow_id = uuid4().hex[:WORKFLOW_ID_LENGTH]
    return await _execute_workflow(req, workflow_id, raise_on_failure=True, persist_initial=True)


async def start_workflow(req: RunWorkflowRequest) -> WorkflowResult:
    """Startuje workflow asynchronicznie i zwraca natychmiastowy snapshot running."""
    workflow_id = uuid4().hex[:WORKFLOW_ID_LENGTH]
    initial = WorkflowResult(
        workflow_id=workflow_id,
        name=req.name,
        status=StepStatus.RUNNING,
    )
    await _persist_workflow_snapshot(req, initial)

    task = asyncio.create_task(
        _execute_workflow(req, workflow_id, raise_on_failure=False, persist_initial=False)
    )
    _track_background_task(task)
    log.info("↗ Workflow '%s' [%s] started in background", req.name, workflow_id)
    return initial
