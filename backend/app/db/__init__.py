"""
Database layer — persystencja workflow history w Postgres.

Factory function `create_workflow_repo()` zwraca odpowiednią
implementację na podstawie env POSTGRES_URL:
  - set    → PostgresWorkflowRepo
  - unset  → MemoryWorkflowRepo (fallback)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class WorkflowRepo(ABC):
    """Abstrakcja persystencji workflow."""

    @abstractmethod
    async def save_run(self, workflow_id: str, name: str, status: str, data: dict) -> None:
        ...

    @abstractmethod
    async def update_run_status(self, workflow_id: str, status: str) -> None:
        ...

    @abstractmethod
    async def get_run(self, workflow_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        ...

    @abstractmethod
    async def count_runs(self) -> int:
        ...


def create_workflow_repo() -> WorkflowRepo:
    """Factory: zwraca Postgres repo jeśli URL jest ustawiony, inaczej memory."""
    pg_url = os.getenv("POSTGRES_URL")
    if pg_url:
        from .postgres import PostgresWorkflowRepo
        return PostgresWorkflowRepo(pg_url)
    else:
        from .memory import MemoryWorkflowRepo
        return MemoryWorkflowRepo()
