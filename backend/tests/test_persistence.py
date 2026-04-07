"""
Tests for workflow persistence — MemoryWorkflowRepo and factory.

Tests: CRUD, list ordering, count, update status, factory fallback,
max_size eviction.
"""

from __future__ import annotations

import pytest
from app.db.memory import MemoryWorkflowRepo

# ── MemoryWorkflowRepo CRUD ─────────────────────────────────────


class TestMemoryRepoCRUD:
    """Basic CRUD on MemoryWorkflowRepo."""

    @pytest.fixture
    def repo(self):
        """Fresh in-memory repo per test."""
        return MemoryWorkflowRepo()

    async def test_save_and_get(self, repo) -> None:
        """Save a workflow run, retrieve by ID."""
        await repo.save_run(
            workflow_id="wf1",
            name="test_workflow",
            status="completed",
            data={"trigger": "manual", "steps": [{"action": "send_invoice"}]},
        )
        result = await repo.get_run("wf1")
        assert result is not None
        assert result["workflow_id"] == "wf1"
        assert result["name"] == "test_workflow"
        assert result["status"] == "completed"
        assert result["trigger"] == "manual"

    async def test_get_nonexistent(self, repo) -> None:
        """Get non-existent workflow → None."""
        result = await repo.get_run("missing")
        assert result is None

    async def test_update_status(self, repo) -> None:
        """Update workflow run status."""
        await repo.save_run("wf1", "test", "running", {"trigger": "manual", "steps": []})
        await repo.update_run_status("wf1", "completed")
        result = await repo.get_run("wf1")
        assert result["status"] == "completed"

    async def test_update_nonexistent(self, repo) -> None:
        """Update non-existent workflow → no error."""
        await repo.update_run_status("missing", "completed")  # Should not raise

    async def test_count_empty(self, repo) -> None:
        """Empty repo → count 0."""
        assert await repo.count_runs() == 0

    async def test_count_after_saves(self, repo) -> None:
        """Count reflects number of stored runs."""
        for i in range(5):
            await repo.save_run(f"wf{i}", f"test{i}", "completed", {"trigger": "manual", "steps": []})
        assert await repo.count_runs() == 5


# ── List ordering ────────────────────────────────────────────────


class TestMemoryRepoListOrdering:
    """list_runs returns items in reverse insertion order (newest first)."""

    @pytest.fixture
    async def populated_repo(self):
        """Repo with 3 workflow runs."""
        repo = MemoryWorkflowRepo()
        await repo.save_run("wf1", "first", "completed", {"trigger": "manual", "steps": []})
        await repo.save_run("wf2", "second", "completed", {"trigger": "manual", "steps": []})
        await repo.save_run("wf3", "third", "running", {"trigger": "cron", "steps": []})
        return repo

    async def test_list_default(self, populated_repo) -> None:
        """List all runs → newest first."""
        runs = await populated_repo.list_runs()
        assert len(runs) == 3
        assert runs[0]["workflow_id"] == "wf3"
        assert runs[1]["workflow_id"] == "wf2"
        assert runs[2]["workflow_id"] == "wf1"

    async def test_list_with_limit(self, populated_repo) -> None:
        """List with limit → capped results."""
        runs = await populated_repo.list_runs(limit=2)
        assert len(runs) == 2
        assert runs[0]["workflow_id"] == "wf3"

    async def test_list_with_offset(self, populated_repo) -> None:
        """List with offset → skipped items."""
        runs = await populated_repo.list_runs(limit=10, offset=1)
        assert len(runs) == 2
        assert runs[0]["workflow_id"] == "wf2"


# ── Max size eviction ────────────────────────────────────────────


class TestMemoryRepoEviction:
    """MemoryWorkflowRepo enforces max_size."""

    async def test_eviction_oldest(self) -> None:
        """Exceeding max_size evicts the oldest entry."""
        repo = MemoryWorkflowRepo(max_size=3)
        for i in range(5):
            await repo.save_run(f"wf{i}", f"test{i}", "completed", {"trigger": "manual", "steps": []})

        assert await repo.count_runs() == 3
        # Oldest (wf0, wf1) should be evicted
        assert await repo.get_run("wf0") is None
        assert await repo.get_run("wf1") is None
        assert await repo.get_run("wf2") is not None
        assert await repo.get_run("wf3") is not None
        assert await repo.get_run("wf4") is not None


# ── Serialization roundtrip ──────────────────────────────────────


class TestSerializationRoundtrip:
    """Data saved to repo preserves all fields through roundtrip."""

    async def test_steps_json_roundtrip(self) -> None:
        """Complex steps JSONB data survives save→get."""
        repo = MemoryWorkflowRepo()
        steps = [
            {
                "step_id": "s1",
                "action": "send_invoice",
                "status": "completed",
                "result": {"invoice_id": "INV-001", "amount": 1500.0},
            },
            {
                "step_id": "s2",
                "action": "notify_slack",
                "status": "completed",
                "result": {"channel": "#general", "ts": "1234567890.123456"},
            },
        ]
        await repo.save_run(
            workflow_id="wf_round",
            name="roundtrip_test",
            status="completed",
            data={"trigger": "manual", "steps": steps},
        )

        result = await repo.get_run("wf_round")
        assert result["steps"] == steps
        assert result["steps"][0]["result"]["amount"] == 1500.0
        assert result["steps"][1]["result"]["channel"] == "#general"


# ── Factory ──────────────────────────────────────────────────────


class TestWorkflowRepoFactory:
    """create_workflow_repo() factory behavior."""

    def test_factory_returns_memory_without_postgres(self, monkeypatch) -> None:
        """Without POSTGRES_URL → MemoryWorkflowRepo."""
        monkeypatch.delenv("POSTGRES_URL", raising=False)

        from app.db import create_workflow_repo
        repo = create_workflow_repo()
        assert isinstance(repo, MemoryWorkflowRepo)

    def test_factory_returns_postgres_with_url(self, monkeypatch) -> None:
        """With POSTGRES_URL → PostgresWorkflowRepo (class check only, no connection)."""
        try:
            import sqlalchemy  # noqa: F401
        except ImportError:
            pytest.skip("sqlalchemy not installed — Postgres repo tested in Docker only")

        monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@localhost:5432/testdb")

        from app.db import create_workflow_repo
        repo = create_workflow_repo()
        assert type(repo).__name__ == "PostgresWorkflowRepo"
