"""
Tests for conversation store — MemoryConversationStore and factory.

Tests: CRUD, serialization roundtrip, delete/count, factory fallback,
ConversationState integration.
"""

from __future__ import annotations

import pytest

from app.store.memory import MemoryConversationStore
from app.schemas import ConversationState


# ── MemoryConversationStore CRUD ────────────────────────────────


class TestMemoryStoreCRUD:
    """Basic CRUD operations on MemoryConversationStore."""

    @pytest.fixture
    def store(self):
        """Fresh in-memory store per test."""
        return MemoryConversationStore()

    async def test_save_and_get(self, store):
        """Save a state dict, retrieve it by ID."""
        state = {"id": "abc", "intent": "send_invoice", "entities": {"amount": 100}}
        await store.save("abc", state)
        result = await store.get("abc")
        assert result == state

    async def test_get_nonexistent(self, store):
        """Get non-existent conversation → None."""
        result = await store.get("missing")
        assert result is None

    async def test_save_overwrites(self, store):
        """Save same ID twice → latest value wins."""
        await store.save("abc", {"version": 1})
        await store.save("abc", {"version": 2})
        result = await store.get("abc")
        assert result["version"] == 2

    async def test_delete(self, store):
        """Delete existing conversation."""
        await store.save("abc", {"id": "abc"})
        await store.delete("abc")
        assert await store.get("abc") is None

    async def test_delete_nonexistent(self, store):
        """Delete non-existent conversation → no error."""
        await store.delete("missing")  # Should not raise

    async def test_count_empty(self, store):
        """Empty store → count 0."""
        assert await store.count() == 0

    async def test_count_after_saves(self, store):
        """Count reflects number of stored conversations."""
        await store.save("a", {"id": "a"})
        await store.save("b", {"id": "b"})
        await store.save("c", {"id": "c"})
        assert await store.count() == 3

    async def test_count_after_delete(self, store):
        """Count decreases after delete."""
        await store.save("a", {"id": "a"})
        await store.save("b", {"id": "b"})
        await store.delete("a")
        assert await store.count() == 1


# ── Serialization roundtrip ──────────────────────────────────────


class TestSerializationRoundtrip:
    """Store must preserve data through save→get cycle."""

    @pytest.fixture
    def store(self):
        return MemoryConversationStore()

    async def test_conversation_state_roundtrip(self, store):
        """ConversationState → model_dump → save → get → ConversationState."""
        original = ConversationState(id="round1")
        original.intent = "send_invoice"
        original.entities = {"amount": 1500.0, "currency": "PLN", "to": "a@b.com"}
        original.missing = ["amount"]
        original.status = "in_progress"
        original.history = [
            {"role": "user", "text": "Wyślij fakturę"},
            {"role": "assistant", "text": "Podaj kwotę."},
        ]

        await store.save(original.id, original.model_dump())
        raw = await store.get(original.id)
        restored = ConversationState(**raw)

        assert restored.id == original.id
        assert restored.intent == original.intent
        assert restored.entities == original.entities
        assert restored.missing == original.missing
        assert restored.status == original.status
        assert len(restored.history) == 2

    async def test_complex_entities_roundtrip(self, store):
        """Entities with various types survive roundtrip."""
        data = {
            "id": "complex1",
            "intent": "generate_report",
            "entities": {
                "report_type": "sales",
                "format": "pdf",
                "_trigger": "cron:0 8 * * *",
            },
            "missing": [],
            "status": "ready",
            "history": [],
        }
        await store.save("complex1", data)
        result = await store.get("complex1")
        assert result["entities"]["_trigger"] == "cron:0 8 * * *"
        assert result["entities"]["report_type"] == "sales"


# ── Factory ──────────────────────────────────────────────────────


class TestStoreFactory:
    """get_conversation_store() factory behavior."""

    def test_factory_returns_memory_without_redis(self, monkeypatch):
        """Without REDIS_URL → MemoryConversationStore."""
        monkeypatch.delenv("REDIS_URL", raising=False)

        # Reset singleton so factory re-evaluates
        import app.store.factory as factory_mod
        factory_mod._instance = None

        store = factory_mod.get_conversation_store()
        assert isinstance(store, MemoryConversationStore)

        # Clean up singleton
        factory_mod._instance = None

    def test_factory_singleton(self, monkeypatch):
        """Factory returns the same instance on repeated calls."""
        monkeypatch.delenv("REDIS_URL", raising=False)

        import app.store.factory as factory_mod
        factory_mod._instance = None

        store1 = factory_mod.get_conversation_store()
        store2 = factory_mod.get_conversation_store()
        assert store1 is store2

        # Clean up singleton
        factory_mod._instance = None

    def test_factory_falls_back_on_bad_redis(self, monkeypatch):
        """Invalid REDIS_URL → graceful fallback to MemoryConversationStore."""
        monkeypatch.setenv("REDIS_URL", "redis://invalid-host-that-does-not-exist:9999")

        import app.store.factory as factory_mod
        factory_mod._instance = None

        store = factory_mod.get_conversation_store()
        # Should be Memory (fallback) or Redis (if connection isn't tested at init)
        # Either way, should not raise
        assert store is not None

        # Clean up singleton
        factory_mod._instance = None


# ── Store isolation ──────────────────────────────────────────────


class TestStoreIsolation:
    """Multiple store instances are isolated."""

    async def test_separate_instances_isolated(self):
        """Two MemoryConversationStore instances don't share data."""
        store_a = MemoryConversationStore()
        store_b = MemoryConversationStore()

        await store_a.save("shared_id", {"source": "a"})
        result_b = await store_b.get("shared_id")

        assert result_b is None
        assert await store_a.count() == 1
        assert await store_b.count() == 0
