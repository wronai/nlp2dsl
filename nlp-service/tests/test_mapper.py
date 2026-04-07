"""
Tests for nlp-service/app/mapper.py — NLP→DSL deterministic mapping.

Tests real mapping logic: NLPResult → WorkflowDSL / DialogResponse.
"""

from __future__ import annotations

import pytest
from app.mapper import _resolve_actions, map_to_dsl
from app.registry import ACTIONS_REGISTRY, BUSINESS_ACTIONS
from app.schemas import (
    NLPEntities,
    NLPIntent,
    NLPResult,
)

# ── Complete mapping ─────────────────────────────────────────────


class TestMapCompleteDSL:
    """Cases where all required fields are present → complete DSL."""

    def test_map_complete_invoice(self) -> None:
        """Full invoice NLPResult → complete WorkflowDSL with 1 step."""
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.9),
            entities=NLPEntities(amount=1500.0, currency="PLN", to="klient@firma.pl"),
            raw_text="Wyślij fakturę na 1500 PLN do klient@firma.pl",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "complete"
        assert dialog.workflow is not None
        assert len(dialog.workflow.steps) == 1
        step = dialog.workflow.steps[0]
        assert step.action == "send_invoice"
        assert step.config["amount"] == 1500.0
        assert step.config["to"] == "klient@firma.pl"

    def test_map_complete_email(self) -> None:
        """Email with recipient → complete DSL."""
        nlp = NLPResult(
            intent=NLPIntent(intent="send_email", confidence=0.8),
            entities=NLPEntities(to="jan@example.com"),
            raw_text="Wyślij email do jan@example.com",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "complete"
        assert dialog.workflow.steps[0].action == "send_email"
        assert dialog.workflow.steps[0].config["to"] == "jan@example.com"


# ── Incomplete mapping ───────────────────────────────────────────


class TestMapIncomplete:
    """Cases where required fields are missing → DialogResponse with prompt."""

    def test_map_incomplete_invoice(self) -> None:
        """Invoice without amount/email → incomplete with missing_fields."""
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.7),
            entities=NLPEntities(),
            raw_text="Wyślij fakturę",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "incomplete"
        assert len(dialog.missing_fields) > 0
        assert any("amount" in f for f in dialog.missing_fields)
        assert any("to" in f for f in dialog.missing_fields)
        assert dialog.prompt_user is not None


# ── Composite mapping ────────────────────────────────────────────


class TestMapComposite:
    """Composite intent mapping (multi-step workflows)."""

    def test_map_composite_report_email(self) -> None:
        """report_and_email → 2-step DSL (generate_report + send_email)."""
        nlp = NLPResult(
            intent=NLPIntent(intent="report_and_email", confidence=0.9),
            entities=NLPEntities(
                report_type="sales", format="pdf", to="boss@corp.com"
            ),
            raw_text="Raport sprzedaży PDF i wyślij na boss@corp.com",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "complete"
        assert len(dialog.workflow.steps) == 2
        actions = [s.action for s in dialog.workflow.steps]
        assert "generate_report" in actions
        assert "send_email" in actions


# ── Unknown intent ───────────────────────────────────────────────


class TestMapUnknown:
    """Unknown intent → error response."""

    def test_map_unknown_intent(self) -> None:
        """Unrecognized intent → status 'error' with message."""
        nlp = NLPResult(
            intent=NLPIntent(intent="unknown", confidence=0.2),
            entities=NLPEntities(),
            raw_text="zrób coś fajnego",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "error"
        assert dialog.prompt_user is not None

    def test_map_nonexistent_intent(self) -> None:
        """Completely fabricated intent → error."""
        nlp = NLPResult(
            intent=NLPIntent(intent="teleport_to_moon", confidence=0.1),
            entities=NLPEntities(),
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "error"


# ── Defaults ─────────────────────────────────────────────────────


class TestMapDefaults:
    """Optional fields receive default values from registry."""

    def test_map_with_defaults(self) -> None:
        """Invoice with amount+to but no currency → default PLN."""
        nlp = NLPResult(
            intent=NLPIntent(intent="send_invoice", confidence=0.9),
            entities=NLPEntities(amount=500.0, to="user@example.com"),
            raw_text="Faktura 500 do user@example.com",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "complete"
        step = dialog.workflow.steps[0]
        assert step.config.get("currency") == "PLN"


# ── Trigger propagation ─────────────────────────────────────────


class TestMapTrigger:
    """Trigger extracted from raw_text propagates to DSL."""

    def test_map_trigger_propagation(self) -> None:
        """Weekly trigger in text → workflow.trigger == 'weekly'."""
        nlp = NLPResult(
            intent=NLPIntent(intent="generate_report", confidence=0.9),
            entities=NLPEntities(report_type="sales", format="pdf"),
            raw_text="co tydzień raport sprzedaży w PDF",
        )
        dialog = map_to_dsl(nlp)
        assert dialog.status == "complete"
        assert dialog.workflow.trigger == "weekly"


# ── System actions ───────────────────────────────────────────────


class TestMapSystemAction:
    """System intents should not map to DSL (no steps for system actions)."""

    def test_map_system_action_settings(self) -> None:
        """system_settings_get has no required fields → complete but 0-step DSL or handled elsewhere."""
        nlp = NLPResult(
            intent=NLPIntent(intent="system_settings_get", confidence=0.9),
            entities=NLPEntities(),
        )
        dialog = map_to_dsl(nlp)
        # System actions are in registry, so they map to a DSL step
        # (orchestrator handles them separately, mapper just builds DSL)
        assert dialog.status == "complete"


# ── All business actions ─────────────────────────────────────────


class TestMapAllBusinessActions:
    """Ensure mapper handles all registered business actions."""

    # Actions whose required fields are fully representable in NLPEntities
    _ENTITY_FIELDS = set(NLPEntities.model_fields.keys())

    @pytest.mark.parametrize("action_name", sorted(BUSINESS_ACTIONS))
    def test_map_all_business_actions(self, action_name) -> None:
        """Each business action with all required fields → complete DSL (if fields exist in NLPEntities)."""
        meta = ACTIONS_REGISTRY[action_name]
        # Build entities with dummy values for required fields
        entity_kwargs = {}
        has_unmapped_fields = False
        for field in meta["required"]:
            if field not in self._ENTITY_FIELDS:
                has_unmapped_fields = True
                continue
            if field == "amount":
                entity_kwargs["amount"] = 100.0
            elif field == "to":
                entity_kwargs["to"] = "test@example.com"
            elif field == "report_type":
                entity_kwargs["report_type"] = "sales"
            elif field == "channel":
                entity_kwargs["channel"] = "#test"
            elif field == "entity":
                entity_kwargs["entity"] = "contact"
            else:
                entity_kwargs[field] = "test_value"

        nlp = NLPResult(
            intent=NLPIntent(intent=action_name, confidence=0.9),
            entities=NLPEntities(**entity_kwargs),
            raw_text="test",
        )
        dialog = map_to_dsl(nlp)
        if has_unmapped_fields:
            # Actions with fields not in NLPEntities will be incomplete
            assert dialog.status in ("complete", "incomplete")
        else:
            assert dialog.status == "complete", (
                f"Action '{action_name}' failed: missing={dialog.missing_fields}"
            )


# ── Internal helpers ─────────────────────────────────────────────


class TestResolveActions:
    """_resolve_actions helper tests."""

    def test_resolve_direct_action(self) -> None:
        """Direct action name → single-item list."""
        assert _resolve_actions("send_invoice") == ["send_invoice"]

    def test_resolve_composite_intent(self) -> None:
        """Named composite → list of constituent actions."""
        actions = _resolve_actions("invoice_and_notify")
        assert "send_invoice" in actions
        assert "notify_slack" in actions

    def test_resolve_dynamic_composite(self) -> None:
        """Dynamic _and_ composite → resolved parts."""
        actions = _resolve_actions("send_invoice_and_send_email")
        assert "send_invoice" in actions
        assert "send_email" in actions

    def test_resolve_unknown(self) -> None:
        """Unknown intent → empty list."""
        assert _resolve_actions("teleport") == []
