"""
Workflow Engine — tłumaczy deklaratywny DSL na imperatywne wykonanie.

Współdzielony moduł: run_workflow() + _repo singleton używany przez wszystkie routery.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from httpx import AsyncClient

from .config import settings
from .db import create_workflow_repo
from .logging_setup import get_request_id
from .schemas import (
    RunWorkflowRequest,
    StepResult,
    StepStatus,
    WorkflowResult,
)

log = logging.getLogger("workflow-engine")

WORKER_URL = settings.worker_url
NLP_SERVICE_URL = settings.nlp_service_url

_repo = create_workflow_repo()


async def run_workflow(req: RunWorkflowRequest) -> WorkflowResult:
    """Uruchamia workflow — iteruje po krokach DSL i deleguje do workera."""
    workflow_id = uuid4().hex[:12]
    result = WorkflowResult(
        workflow_id=workflow_id,
        name=req.name,
        status=StepStatus.RUNNING,
    )

    log.info("▶ Workflow '%s' [%s] — %d steps", req.name, workflow_id, len(req.steps))

    trace_headers = {"X-Request-ID": get_request_id()}

    async with AsyncClient(timeout=120.0, headers=trace_headers) as client:
        for step in req.steps:
            step_result = StepResult(
                step_id=step.id,
                action=step.action,
                status=StepStatus.RUNNING,
                started_at=datetime.utcnow(),
            )

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

            step_result.finished_at = datetime.utcnow()
            result.steps.append(step_result)

            if step_result.status == StepStatus.FAILED:
                result.status = StepStatus.FAILED
                await _repo.save_run(
                    workflow_id=workflow_id,
                    name=req.name,
                    status=result.status.value,
                    data={"trigger": req.trigger or "manual", "steps": [s.model_dump(mode="json") for s in result.steps]},
                )
                raise HTTPException(
                    status_code=400,
                    detail={"workflow_id": workflow_id, "failed_step": step.id, "error": step_result.error},
                )

    result.status = StepStatus.COMPLETED
    await _repo.save_run(
        workflow_id=workflow_id,
        name=req.name,
        status=result.status.value,
        data={"trigger": req.trigger or "manual", "steps": [s.model_dump(mode="json") for s in result.steps]},
    )
    log.info("✔ Workflow '%s' [%s] completed", req.name, workflow_id)
    return result
