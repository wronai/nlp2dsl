"""
Schemas — deklaratywny DSL procesu automatyzacji.

Użytkownik opisuje CO chce zrobić (kroki workflow),
system sam tłumaczy to na imperatywne wykonanie w kontenerach.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# ── Workflow DSL ──────────────────────────────────────────────

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Step(BaseModel):
    """Pojedynczy krok workflow — deklaratywny opis akcji."""
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    action: str          # np. "send_invoice", "send_email", "generate_report"
    config: dict = {}    # parametry akcji


class RunWorkflowRequest(BaseModel):
    """Żądanie uruchomienia workflow — DSL biznesowy."""
    name: str
    steps: list[Step]
    trigger: str | None = None   # np. "manual", "weekly", "on_event"


# ── Responses ─────────────────────────────────────────────────

class StepResult(BaseModel):
    step_id: str
    action: str
    status: StepStatus
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkflowResult(BaseModel):
    workflow_id: str
    name: str
    status: StepStatus
    steps: list[StepResult] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Registry ──────────────────────────────────────────────────

class ActionInfo(BaseModel):
    """Opis dostępnej akcji (do listowania w GUI / API)."""
    name: str
    description: str
    config_schema: dict = {}
