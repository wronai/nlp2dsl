"""Tests for nlp-service action catalog proxy (C1)."""

from __future__ import annotations

from app.action_catalog import nlp_actions_to_action_info


def test_nlp_actions_to_action_info_maps_fields() -> None:
    payload = {
        "send_invoice": {
            "description": "Generuje i wysyła fakturę",
            "required": ["amount", "to"],
            "optional": ["currency"],
            "aliases": ["faktura"],
        },
        "send_email": {
            "description": "Wysyła e-mail",
            "required": ["to"],
            "optional": ["subject", "body"],
            "aliases": [],
        },
    }
    actions = nlp_actions_to_action_info(payload)
    assert [a.name for a in actions] == ["send_email", "send_invoice"]
    invoice = next(a for a in actions if a.name == "send_invoice")
    assert invoice.description == "Generuje i wysyła fakturę"
    assert invoice.config_schema["amount"] == "float"
    assert invoice.config_schema["currency"] == "str"


def test_required_and_quality_fields_from_catalog() -> None:
    from app.action_catalog import (
        load_action_field_catalog,
        quality_fields_for_action,
        required_fields_for_action,
    )

    catalog = {
        "send_email": {
            "required": ["to"],
            "quality_required": ["body"],
        }
    }
    assert required_fields_for_action("send_email", catalog=catalog) == ["to"]
    assert quality_fields_for_action("send_email", catalog=catalog) == ["body"]


def test_load_action_field_catalog_uses_fallback_when_unreachable(monkeypatch) -> None:
    from app import action_catalog

    action_catalog._CATALOG_CACHE = None
    monkeypatch.setattr(action_catalog, "_default_nlp_service_url", lambda: "http://127.0.0.1:1")
    catalog = action_catalog.load_action_field_catalog(force=True)
    assert "send_invoice" in catalog
    assert catalog["send_invoice"]["required"] == ["amount", "to"]
