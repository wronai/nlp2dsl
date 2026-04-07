"""
Database layer — persystencja workflow history w Postgres.

Factory function `create_workflow_repo()` zwraca odpowiednią
implementację na podstawie env POSTGRES_URL:
  - set    → PostgresWorkflowRepo
  - unset  → MemoryWorkflowRepo (fallback)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class WorkflowRepo(ABC):
    """Abstrakcja persystencji workflow."""

    @abstractmethod
    async def save_run(self, workflow_id: str, name: str, status: str, data: dict) -> None:
        ...

    @abstractmethod
    async def update_run_status(self, workflow_id: str, status: str) -> None:
        ...

    @abstractmethod
    async def get_run(self, workflow_id: str) -> dict | None:
        ...

    @abstractmethod
    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        ...

    @abstractmethod
    async def count_runs(self) -> int:
        ...


def create_workflow_repo() -> WorkflowRepo:
    """Factory: zwraca Postgres repo jeśli URL jest ustawiony, inaczej memory."""
    from app.config import settings
    pg_url = settings.postgres_url
    if pg_url:
        from .postgres import PostgresWorkflowRepo
        return PostgresWorkflowRepo(pg_url)
    from .memory import MemoryWorkflowRepo
    return MemoryWorkflowRepo()
