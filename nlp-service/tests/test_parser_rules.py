"""
Tests for nlp-service/app/parser_rules.py — rule-based NLP parser.

Tests real parsing logic (no mocks) on Polish and English text inputs.
"""

from __future__ import annotations

import pytest
from app.parser_rules import parse_rules
from app.schemas import NLPResult

# ── Invoice parsing ──────────────────────────────────────────────


class TestParseInvoice:
    """Invoice intent detection and entity extraction."""

    def test_parse_invoice_simple(self) -> None:
        """Complete invoice request: amount + currency + email."""
        result = parse_rules("Wyślij fakturę na 1500 PLN do klient@firma.pl")
        assert result.intent.intent == "send_invoice"
        assert result.entities.amount == 1500.0
        assert result.entities.currency == "PLN"
        assert result.entities.to == "klient@firma.pl"
        assert result.intent.confidence >= 0.6

    def test_parse_invoice_missing_data(self) -> None:
        """Incomplete invoice — no amount, no email. Still detects intent."""
        result = parse_rules("Wyślij fakturę")
        assert result.intent.intent == "send_invoice"
        assert result.entities.amount is None
        assert result.entities.to is None

    def test_parse_invoice_eur(self) -> None:
        """Invoice with EUR currency."""
        result = parse_rules("Faktura na 2500 EUR do jan@example.com")
        assert result.intent.intent == "send_invoice"
        assert result.entities.amount == 2500.0
        assert result.entities.currency == "EUR"
        assert result.entities.to == "jan@example.com"

    def test_parse_invoice_usd(self) -> None:
        """Invoice with USD currency — English text."""
        result = parse_rules("Invoice for 999.50 USD to billing@corp.com")
        assert result.intent.intent == "send_invoice"
        assert result.entities.amount == 999.50
        assert result.entities.currency == "USD"
        assert result.entities.to == "billing@corp.com"


# ── Email parsing ────────────────────────────────────────────────


class TestParseEmail:
    """Email intent detection."""

    def test_parse_email(self) -> None:
        """Simple email request with recipient."""
        result = parse_rules("Napisz maila do jan@example.com")
        assert result.intent.intent == "send_email"
        assert result.entities.to == "jan@example.com"

    def test_parse_email_english(self) -> None:
        """English email request."""
        result = parse_rules("Send email to admin@corp.com")
        assert result.intent.intent == "send_email"
        assert result.entities.to == "admin@corp.com"


# ── Report parsing ───────────────────────────────────────────────


class TestParseReport:
    """Report intent and entity extraction."""

    def test_parse_report_weekly(self) -> None:
        """Weekly sales report in PDF — detects trigger + report_type + format."""
        result = parse_rules("Co tydzień raport sprzedaży w PDF")
        assert result.intent.intent == "generate_report"
        assert result.entities.report_type == "sales"
        assert result.entities.format == "pdf"

    def test_parse_report_finance_csv(self) -> None:
        """Finance report in CSV format."""
        result = parse_rules("Generuj raport finansowy w CSV")
        assert result.intent.intent == "generate_report"
        assert result.entities.report_type == "finance"
        assert result.entities.format == "csv"


# ── Composite intents ────────────────────────────────────────────


class TestParseComposite:
    """Multi-action (composite) intent detection."""

    def test_parse_composite_invoice_notify(self) -> None:
        """Invoice + Slack notification → composite intent."""
        result = parse_rules(
            "Wyślij fakturę na 1500 PLN do klient@firma.pl i powiadom na Slacku #general"
        )
        # Should detect both send_invoice and notify_slack
        intent = result.intent.intent
        assert "send_invoice" in intent or "invoice_and_notify" in intent
        assert result.entities.amount == 1500.0
        assert result.entities.channel == "#general"

    def test_parse_composite_full_flow(self) -> None:
        """Invoice + email + Slack → full_invoice_flow or triple composite."""
        result = parse_rules(
            "Faktura na 3000 PLN do boss@corp.com plus email i Slack #sales"
        )
        intent = result.intent.intent
        # Should detect at least two actions
        assert intent != "unknown"
        assert result.entities.amount == 3000.0


# ── System commands ──────────────────────────────────────────────


class TestParseSystem:
    """System intent detection (settings, files, status)."""

    def test_parse_system_settings(self) -> None:
        """Settings inquiry → system_settings_get."""
        result = parse_rules("pokaż ustawienia")
        assert result.intent.intent == "system_settings_get"

    def test_parse_system_file_list(self) -> None:
        """File listing → system_file_list."""
        result = parse_rules("pokaż pliki")
        assert result.intent.intent == "system_file_list"

    def test_parse_system_status(self) -> None:
        """System status → system_status."""
        result = parse_rules("status systemu")
        assert result.intent.intent == "system_status"

    def test_parse_system_help(self) -> None:
        """Help / action listing → system_registry_list."""
        result = parse_rules("jakie akcje")
        assert result.intent.intent == "system_registry_list"


# ── Unknown intent ───────────────────────────────────────────────


class TestParseUnknown:
    """Unknown input handling."""

    def test_parse_unknown(self) -> None:
        """Unrecognized text → intent 'unknown' with low confidence."""
        result = parse_rules("zrób coś fajnego")
        assert result.intent.intent == "unknown"
        assert result.intent.confidence <= 0.5


# ── Amount extraction ────────────────────────────────────────────


class TestAmountExtraction:
    """Currency and amount parsing across formats."""

    @pytest.mark.parametrize(
        "text,expected_amount,expected_currency",
        [
            ("faktura na 1500 PLN", 1500.0, "PLN"),
            ("invoice 2500 EUR", 2500.0, "EUR"),
            ("rachunek 999.50 USD", 999.50, "USD"),
            ("faktura na 100 zł", 100.0, "PLN"),
        ],
    )
    def test_parse_amount_extraction(self, text, expected_amount, expected_currency) -> None:
        """Extract amount and currency from various formats."""
        result = parse_rules(text)
        assert result.entities.amount == expected_amount
        assert result.entities.currency == expected_currency


# ── Trigger detection ────────────────────────────────────────────


class TestTriggerDetection:
    """Schedule trigger extraction from text."""

    @pytest.mark.parametrize(
        "text,expected_trigger",
        [
            ("Codziennie wysyłaj raport sprzedaży", "daily"),
            ("Co tydzień raport HR", "weekly"),
            ("Co miesiąc generuj raport", "monthly"),
        ],
    )
    def test_parse_trigger_detection(self, text, expected_trigger) -> None:
        """Detect schedule triggers in text."""
        from app.registry import get_trigger

        trigger = get_trigger(text)
        assert trigger == expected_trigger


# ── Result structure ─────────────────────────────────────────────


class TestResultStructure:
    """NLPResult output structure validation."""

    def test_result_is_nlp_result(self) -> None:
        """parse_rules returns NLPResult instance."""
        result = parse_rules("faktura")
        assert isinstance(result, NLPResult)
        assert hasattr(result, "intent")
        assert hasattr(result, "entities")
        assert hasattr(result, "raw_text")

    def test_raw_text_preserved(self) -> None:
        """raw_text field contains original input."""
        text = "Wyślij fakturę na 500 PLN"
        result = parse_rules(text)
        assert result.raw_text == text
