"""
Fixtures for nlp-service unit tests.

Provides sample texts (PL/EN), expected intents, sample entities,
and mock conversation store for orchestrator tests.
"""

from __future__ import annotations

import pytest

from app.store.memory import MemoryConversationStore


# ── Sample texts for NLP parsing ─────────────────────────────────


@pytest.fixture
def sample_texts() -> dict[str, str]:
    """15+ example texts in PL and EN for parser testing."""
    return {
        # Invoice
        "invoice_complete": "Wyślij fakturę na 1500 PLN do klient@firma.pl",
        "invoice_missing": "Wyślij fakturę",
        "invoice_eur": "Faktura na 2500 EUR do jan@example.com",
        "invoice_usd": "Invoice for 999.50 USD to billing@corp.com",
        # Email
        "email_simple": "Napisz maila do jan@example.com",
        "email_with_subject": "Wyślij email do anna@test.pl temat: Spotkanie",
        # Report
        "report_weekly": "Co tydzień raport sprzedaży w PDF",
        "report_finance_csv": "Generuj raport finansowy w CSV",
        # Composite
        "composite_invoice_notify": "Wyślij fakturę na 1500 PLN do klient@firma.pl i powiadom na Slacku #general",
        "composite_full_flow": "Faktura na 3000 PLN do boss@corp.com plus email i Slack #sales",
        # System
        "system_settings": "pokaż ustawienia",
        "system_file_list": "pokaż pliki",
        "system_status": "status systemu",
        "system_help": "jakie akcje",
        # Unknown
        "unknown": "zrób coś fajnego",
        # Trigger
        "trigger_daily": "Codziennie wysyłaj raport sprzedaży w PDF",
        "trigger_monthly": "Co miesiąc generuj raport finansowy",
    }


@pytest.fixture
def expected_intents() -> dict[str, str]:
    """Mapping: sample_texts key → expected intent name."""
    return {
        "invoice_complete": "send_invoice",
        "invoice_missing": "send_invoice",
        "invoice_eur": "send_invoice",
        "invoice_usd": "send_invoice",
        "email_simple": "send_email",
        "email_with_subject": "send_email",
        "report_weekly": "generate_report",
        "report_finance_csv": "generate_report",
        "system_settings": "system_settings_get",
        "system_file_list": "system_file_list",
        "system_status": "system_status",
        "system_help": "system_registry_list",
        "unknown": "unknown",
    }


@pytest.fixture
def sample_entities() -> dict[str, dict]:
    """Expected entities after parsing specific texts."""
    return {
        "invoice_complete": {
            "amount": 1500.0,
            "currency": "PLN",
            "to": "klient@firma.pl",
        },
        "invoice_eur": {
            "amount": 2500.0,
            "currency": "EUR",
            "to": "jan@example.com",
        },
        "email_simple": {
            "to": "jan@example.com",
        },
    }


@pytest.fixture
def mock_conversation_store() -> MemoryConversationStore:
    """In-memory conversation store for testing."""
    return MemoryConversationStore()
