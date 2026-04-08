"""
Workflow events — lekki in-memory broker dla statusów workflow.

Wersja production-friendly bez zewnętrznego brokera:
- backend publikuje lifecycle events w trakcie wykonania workflow,
- SSE endpoint może je streamować do przeglądarki,
- repozytorium Postgres dalej przechowuje aktualny snapshot runa.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

TERMINAL_EVENT_TYPES = {"workflow_completed", "workflow_failed"}


@dataclass(slots=True)
class WorkflowEvent:
    workflow_id: str
    event_type: str
    status: str
    message: str
    step_id: str | None = None
    action: str | None = None
    step_index: int | None = None
    total_steps: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.event_type in TERMINAL_EVENT_TYPES

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "workflow_id": self.workflow_id,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "step_id": self.step_id,
            "action": self.action,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "terminal": self.is_terminal,
        }


class WorkflowEventHub:
    """In-memory broadcaster dla workflow lifecycle events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[WorkflowEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, workflow_id: str) -> asyncio.Queue[WorkflowEvent]:
        queue: asyncio.Queue[WorkflowEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers[workflow_id].add(queue)
        return queue

    async def unsubscribe(self, workflow_id: str, queue: asyncio.Queue[WorkflowEvent]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(workflow_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(workflow_id, None)

    async def publish(self, event: WorkflowEvent) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(event.workflow_id, set()))

        for queue in subscribers:
            await queue.put(event)

    async def subscriber_count(self, workflow_id: str) -> int:
        async with self._lock:
            return len(self._subscribers.get(workflow_id, set()))


workflow_event_hub = WorkflowEventHub()
