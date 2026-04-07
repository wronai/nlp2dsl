"""
Tests for nlp-service/app/orchestrator.py — conversation state management.

Uses MemoryConversationStore (no Redis needed).
Patches the global _store to use a test-local store instance.
"""

from __future__ import annotations

import pytest

from app.orchestrator import (
    start_conversation,
    continue_conversation,
    get_conversation,
    get_action_form,
    _process_message,
    _merge_into_state,
)
from app.schemas import ConversationState, ConversationResponse, NLPResult, NLPIntent, NLPEntities
from app.store.memory import MemoryConversationStore


@pytest.fixture(autouse=True)
def _patch_store(monkeypatch):
    """Replace orchestrator's _store with a fresh MemoryConversationStore per test."""
    import app.orchestrator as orch_mod
    store = MemoryConversationStore()
    monkeypatch.setattr(orch_mod, "_store", store)


# ── start_conversation ───────────────────────────────────────────


class TestStartConversation:
    """Starting a new conversation from initial user text."""

    @pytest.mark.asyncio
    async def test_start_conversation_complete(self):
        """Complete input → status 'ready' with DSL."""
        resp = await start_conversation(
            "Wyślij fakturę na 1500 PLN do klient@firma.pl"
        )
        assert isinstance(resp, ConversationResponse)
        assert resp.conversation_id
        assert resp.status == "ready"
        assert resp.dsl is not None
        assert resp.dsl.steps[0].action == "send_invoice"

    @pytest.mark.asyncio
    async def test_start_conversation_incomplete(self):
        """Incomplete input → status 'in_progress' asking for missing data."""
        resp = await start_conversation("Wyślij fakturę")
        assert resp.status == "in_progress"
        assert resp.message is not None
        # Missing fields should be listed
        assert resp.missing or "kwotę" in resp.message.lower() or "Podaj" in resp.message

    @pytest.mark.asyncio
    async def test_start_conversation_unknown(self):
        """Unrecognized text → in_progress with help message."""
        resp = await start_conversation("zrób coś fajnego")
        assert resp.status == "in_progress"
        assert resp.message is not None


# ── continue_conversation ────────────────────────────────────────


class TestContinueConversation:
    """Multi-turn dialog: providing missing data in follow-up messages."""

    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """Two-turn dialog: start incomplete → provide email → ready."""
        # Turn 1: incomplete invoice
        resp1 = await start_conversation("Wyślij fakturę na 500 PLN")
        cid = resp1.conversation_id
        assert resp1.status == "in_progress"

        # Turn 2: provide email
        resp2 = await continue_conversation(cid, "klient@firma.pl")
        assert resp2.conversation_id == cid
        assert resp2.status == "ready"
        assert resp2.dsl is not None

    @pytest.mark.asyncio
    async def test_continue_conversation_lazy_create(self):
        """Continuing a non-existent conversation creates one lazily."""
        resp = await continue_conversation("nonexistent_id", "Wyślij fakturę na 100 PLN do a@b.pl")
        assert resp.conversation_id == "nonexistent_id"
        assert resp.status in ("ready", "in_progress")


# ── System commands ──────────────────────────────────────────────


class TestSystemCommands:
    """System actions executed directly (no DSL generation)."""

    @pytest.mark.asyncio
    async def test_system_command_status(self):
        """'status' triggers immediate system result."""
        resp = await start_conversation("status systemu")
        assert resp.status == "done"
        assert resp.message is not None

    @pytest.mark.asyncio
    async def test_system_command_settings(self):
        """'pokaż ustawienia' → system_settings_get → done."""
        resp = await start_conversation("pokaż ustawienia")
        assert resp.status == "done"
        assert "stawieni" in resp.message.lower() or "settings" in resp.message.lower() or "{" in resp.message


# ── get_conversation ─────────────────────────────────────────────


class TestGetConversation:
    """Retrieving stored conversation state."""

    @pytest.mark.asyncio
    async def test_get_conversation_exists(self):
        """After start, conversation is retrievable."""
        resp = await start_conversation("faktura na 200 PLN do x@y.pl")
        state = await get_conversation(resp.conversation_id)
        assert state is not None
        assert state.id == resp.conversation_id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self):
        """Non-existent conversation → None."""
        state = await get_conversation("does_not_exist")
        assert state is None


# ── get_action_form ──────────────────────────────────────────────


class TestGetActionForm:
    """Schema-driven UI form generation."""

    def test_action_form_send_invoice(self):
        """send_invoice → form with amount, to, currency fields."""
        form = get_action_form("send_invoice")
        assert form is not None
        assert form.action == "send_invoice"
        field_names = [f.name for f in form.fields]
        assert "amount" in field_names
        assert "to" in field_names

    def test_action_form_nonexistent(self):
        """Unknown action → None."""
        form = get_action_form("nonexistent_action")
        assert form is None


# ── _merge_into_state ────────────────────────────────────────────


class TestMergeIntoState:
    """Internal entity merging logic."""

    def test_merge_updates_intent(self):
        """New NLP result updates state intent."""
        state = ConversationState(id="test")
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.8),
            entities=NLPEntities(amount=100.0),
        )
        _merge_into_state(state, nlp)
        assert state.intent == "send_invoice"
        assert state.entities["amount"] == 100.0

    def test_merge_preserves_existing(self):
        """New NLP with None fields doesn't overwrite existing entities."""
        state = ConversationState(id="test", entities={"amount": 500.0, "to": "a@b.pl"})
        state.intent = "send_invoice"
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.6),
            entities=NLPEntities(currency="EUR"),
        )
        state.history = [{"role": "user", "text": "test"}]
        _merge_into_state(state, nlp)
        assert state.entities["amount"] == 500.0
        assert state.entities["to"] == "a@b.pl"
        assert state.entities["currency"] == "EUR"
