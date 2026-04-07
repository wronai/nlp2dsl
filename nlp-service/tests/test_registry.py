"""
Tests for nlp-service/app/registry.py — actions registry and helpers.

Tests registry structure, alias resolution, trigger detection, helper functions.
"""

from __future__ import annotations

import pytest
from app.registry import (
    ACTIONS_REGISTRY,
    BUSINESS_ACTIONS,
    COMPOSITE_INTENTS,
    SYSTEM_ACTIONS,
    get_action_by_alias,
    get_defaults,
    get_required_fields,
    get_trigger,
)

# ── Registry structure ───────────────────────────────────────────


class TestRegistryStructure:
    """Validate registry entries have required keys."""

    @pytest.mark.parametrize("action_name", ACTIONS_REGISTRY.keys())
    def test_registry_entry_has_required_keys(self, action_name) -> None:
        """Each action must have description, required, optional, aliases."""
        meta = ACTIONS_REGISTRY[action_name]
        assert "description" in meta, f"{action_name} missing 'description'"
        assert "required" in meta, f"{action_name} missing 'required'"
        assert "optional" in meta, f"{action_name} missing 'optional'"
        assert "aliases" in meta, f"{action_name} missing 'aliases'"
        assert isinstance(meta["aliases"], list)
        assert len(meta["aliases"]) > 0, f"{action_name} has no aliases"


# ── Alias resolution ────────────────────────────────────────────


class TestAliasResolution:
    """get_action_by_alias finds best match."""

    def test_alias_invoice_pl(self) -> None:
        """Polish alias 'wyślij fakturę' → send_invoice."""
        assert get_action_by_alias("wyślij fakturę") == "send_invoice"

    def test_alias_email_en(self) -> None:
        """English alias 'send email' → send_email."""
        assert get_action_by_alias("send email") == "send_email"

    def test_alias_report(self) -> None:
        """Polish 'raport' → generate_report."""
        assert get_action_by_alias("raport") == "generate_report"

    def test_alias_slack(self) -> None:
        """'slack' → notify_slack."""
        assert get_action_by_alias("slack") == "notify_slack"

    def test_alias_unknown(self) -> None:
        """Unrecognized text → None."""
        assert get_action_by_alias("quantum teleportation") is None

    def test_alias_best_match(self) -> None:
        """Longest alias wins when multiple match."""
        # "wyślij fakturę" is longer than "fakturę" — should still resolve to send_invoice
        assert get_action_by_alias("wyślij fakturę na 100 PLN") == "send_invoice"


# ── Trigger detection ────────────────────────────────────────────


class TestTriggerDetection:
    """get_trigger extracts schedule from text."""

    def test_trigger_daily(self) -> None:
        """'codziennie' → 'daily'."""
        assert get_trigger("codziennie raporty") == "daily"

    def test_trigger_weekly(self) -> None:
        """'co tydzień' → 'weekly'."""
        assert get_trigger("co tydzień raport") == "weekly"

    def test_trigger_monthly(self) -> None:
        """'co miesiąc' → 'monthly'."""
        assert get_trigger("co miesiąc faktura") == "monthly"

    def test_trigger_manual_default(self) -> None:
        """No trigger keyword → 'manual'."""
        assert get_trigger("wyślij fakturę") == "manual"


# ── Helper functions ─────────────────────────────────────────────


class TestHelperFunctions:
    """get_required_fields, get_defaults."""

    def test_get_required_fields_invoice(self) -> None:
        """send_invoice requires amount and to."""
        fields = get_required_fields("send_invoice")
        assert "amount" in fields
        assert "to" in fields

    def test_get_required_fields_unknown(self) -> None:
        """Unknown action → empty list."""
        assert get_required_fields("nonexistent") == []

    def test_get_defaults_invoice(self) -> None:
        """send_invoice default currency is PLN."""
        defaults = get_defaults("send_invoice")
        assert defaults.get("currency") == "PLN"

    def test_get_defaults_unknown(self) -> None:
        """Unknown action → empty dict."""
        assert get_defaults("nonexistent") == {}


# ── Categories ───────────────────────────────────────────────────


class TestCategories:
    """System vs business action sets."""

    def test_system_actions_nonempty(self) -> None:
        """SYSTEM_ACTIONS set is not empty."""
        assert len(SYSTEM_ACTIONS) > 0

    def test_business_actions_nonempty(self) -> None:
        """BUSINESS_ACTIONS set is not empty."""
        assert len(BUSINESS_ACTIONS) > 0

    def test_no_overlap(self) -> None:
        """System and business sets don't overlap."""
        assert SYSTEM_ACTIONS.isdisjoint(BUSINESS_ACTIONS)

    def test_union_is_complete(self) -> None:
        """System ∪ Business = all actions."""
        assert SYSTEM_ACTIONS | BUSINESS_ACTIONS == set(ACTIONS_REGISTRY.keys())


# ── Composite intents ────────────────────────────────────────────


class TestCompositeIntents:
    """COMPOSITE_INTENTS structure validation."""

    @pytest.mark.parametrize("composite_name", COMPOSITE_INTENTS.keys())
    def test_composite_actions_exist(self, composite_name) -> None:
        """Each action in a composite intent must exist in ACTIONS_REGISTRY."""
        for action in COMPOSITE_INTENTS[composite_name]:
            assert action in ACTIONS_REGISTRY, (
                f"Composite '{composite_name}' references unknown action '{action}'"
            )
