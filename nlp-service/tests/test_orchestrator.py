"""
Tests for nlp-service/app/orchestrator.py — conversation state management.

Uses MemoryConversationStore (no Redis needed).
Patches the global _store to use a test-local store instance.
"""

from __future__ import annotations

import pytest
from app.orchestrator import (
    _format_system_result,
    _merge_into_state,
    continue_conversation,
    get_action_form,
    get_conversation,
    start_conversation,
)
from app.schemas import (
    ConversationResponse,
    ConversationState,
    NLPEntities,
    NLPIntent,
    NLPResult,
)
from app.store.memory import MemoryConversationStore


@pytest.fixture(autouse=True)
def _patch_store(monkeypatch) -> None:
    """Replace orchestrator's _store with a fresh MemoryConversationStore per test."""
    import app.conversation.orchestrator as conv_orch_mod
    import app.orchestrator as orch_mod

    store = MemoryConversationStore()
    monkeypatch.setattr(conv_orch_mod, "_store", store)
    monkeypatch.setattr(orch_mod, "_store", store)


# ── start_conversation ───────────────────────────────────────────


class TestStartConversation:
    """Starting a new conversation from initial user text."""

    @pytest.mark.asyncio
    async def test_start_conversation_complete(self) -> None:
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
    async def test_start_conversation_incomplete(self) -> None:
        """Incomplete input → status 'in_progress' asking for missing data."""
        resp = await start_conversation("Wyślij fakturę")
        assert resp.status == "in_progress"
        assert resp.message is not None
        # Missing fields should be listed
        assert resp.missing or "kwotę" in resp.message.lower() or "Podaj" in resp.message

    @pytest.mark.asyncio
    async def test_start_conversation_unknown(self) -> None:
        """Unrecognized text → in_progress with help message."""
        resp = await start_conversation("zrób coś fajnego")
        assert resp.status == "in_progress"
        assert resp.message is not None


# ── continue_conversation ────────────────────────────────────────


class TestExecuteKeywordMatching:
    def test_go_not_matched_inside_zgodnie(self) -> None:
        from app.conversation.responses import _is_execute_or_continue

        assert not _is_execute_or_continue(
            "Treść: Projekt idzie zgodnie z planem, raport w załączniku."
        )
        assert _is_execute_or_continue("uruchom")


class TestContinueConversation:
    """Multi-turn dialog: providing missing data in follow-up messages."""

    @pytest.mark.asyncio
    async def test_continue_conversation(self) -> None:
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
    async def test_continue_conversation_lazy_create(self) -> None:
        """Continuing a non-existent conversation creates one lazily."""
        resp = await continue_conversation("nonexistent_id", "Wyślij fakturę na 100 PLN do a@b.pl")
        assert resp.conversation_id == "nonexistent_id"
        assert resp.status in ("ready", "in_progress")

    @pytest.mark.asyncio
    async def test_continue_conversation_email_body(self) -> None:
        """Email missing body → provide 'Treść:' follow-up → ready."""
        resp1 = await start_conversation(
            "Wyślij email do team@firma.pl z tematem Status projektu"
        )
        cid = resp1.conversation_id
        assert resp1.status == "in_progress"
        assert resp1.missing and any("body" in f for f in resp1.missing)

        resp2 = await continue_conversation(
            cid,
            "Treść: Projekt idzie zgodnie z planem, raport w załączniku.",
        )
        assert resp2.status == "ready"
        assert resp2.dsl is not None
        assert resp2.dsl.steps[0].config.get("body")


# ── System commands ──────────────────────────────────────────────


class TestSystemCommands:
    """System actions executed directly (no DSL generation)."""

    @pytest.mark.asyncio
    async def test_system_command_status(self) -> None:
        """'status' triggers immediate system result."""
        resp = await start_conversation("status systemu")
        assert resp.status == "done"
        assert resp.message is not None

    @pytest.mark.asyncio
    async def test_system_command_settings(self) -> None:
        """'pokaż ustawienia' → system_settings_get → done."""
        resp = await start_conversation("pokaż ustawienia")
        assert resp.status == "done"
        assert "stawieni" in resp.message.lower() or "settings" in resp.message.lower() or "{" in resp.message

    def test_format_system_file_list(self) -> None:
        """File list formatter keeps the user-facing shape stable."""
        msg = _format_system_result(
            "system_file_list",
            {
                "status": "completed",
                "result": {
                    "directory": ".",
                    "count": 2,
                    "files": [
                        {"path": "a.py", "size_kb": 1},
                        {"path": "b.py", "size_kb": 2},
                    ],
                },
            },
        )
        assert msg == "Pliki w . (2):\n  a.py (1 KB)\n  b.py (2 KB)"

    def test_format_system_failed_result(self) -> None:
        """Failed system action bypasses formatter dispatch."""
        msg = _format_system_result(
            "system_status",
            {"status": "failed", "error": "boom"},
        )
        assert msg == "Błąd: boom"


# ── get_conversation ─────────────────────────────────────────────


class TestGetConversation:
    """Retrieving stored conversation state."""

    @pytest.mark.asyncio
    async def test_get_conversation_exists(self) -> None:
        """After start, conversation is retrievable."""
        resp = await start_conversation("faktura na 200 PLN do x@y.pl")
        state = await get_conversation(resp.conversation_id)
        assert state is not None
        assert state.id == resp.conversation_id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self) -> None:
        """Non-existent conversation → None."""
        state = await get_conversation("does_not_exist")
        assert state is None


# ── get_action_form ──────────────────────────────────────────────


class TestGetActionForm:
    """Schema-driven UI form generation."""

    def test_action_form_send_invoice(self) -> None:
        """send_invoice → form with amount, to, currency fields."""
        form = get_action_form("send_invoice")
        assert form is not None
        assert form.action == "send_invoice"
        field_names = [f.name for f in form.fields]
        assert "amount" in field_names
        assert "to" in field_names

    def test_action_form_nonexistent(self) -> None:
        """Unknown action → None."""
        form = get_action_form("nonexistent_action")
        assert form is None


# ── _merge_into_state ────────────────────────────────────────────


class TestMergeIntoState:
    """Internal entity merging logic."""

    def test_merge_updates_intent(self) -> None:
        """New NLP result updates state intent."""
        state = ConversationState(id="test")
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.8),
            entities=NLPEntities(amount=100.0),
        )
        _merge_into_state(state, nlp)
        assert state.intent == "send_invoice"
        assert state.entities["amount"] == 100.0

    def test_merge_preserves_existing(self) -> None:
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
