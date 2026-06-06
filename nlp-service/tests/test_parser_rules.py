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

    def test_parse_email_reminder(self) -> None:
        """Reminder phrasing maps to send_email with subject."""
        result = parse_rules("Przypomnij billing@firma.pl o nieopłaconej fakturze")
        assert result.intent.intent == "send_email"
        assert result.entities.to == "billing@firma.pl"
        assert result.entities.subject == "Nieopłaconej fakturze"
        assert "Przypominamy" in (result.entities.message or "")

    def test_parse_email_with_subject(self) -> None:
        """'z tematem' extracts subject from email request."""
        result = parse_rules("Wyślij email do team@firma.pl z tematem Status projektu")
        assert "send_email" in result.intent.intent
        assert result.entities.to == "team@firma.pl"
        assert result.entities.subject == "Status projektu"

    def test_parse_email_subject_and_body_same_line(self) -> None:
        """'z tematem X. Treść: Y' splits subject and body on one line."""
        result = parse_rules(
            "Wyślij email do team@firma.pl z tematem Status dzienny. "
            "Treść: Wszystkie projekty przebiegają zgodnie z harmonogramem."
        )
        assert result.entities.to == "team@firma.pl"
        assert result.entities.subject == "Status dzienny"
        assert result.entities.message == "Wszystkie projekty przebiegają zgodnie z harmonogramem."

    def test_parse_email_colon_body(self) -> None:
        """'Napisz do X: treść' extracts message body."""
        result = parse_rules("Napisz do manager@firma.pl: Projekt zakończony sukcesem")
        assert result.intent.intent == "send_email"
        assert result.entities.to == "manager@firma.pl"
        assert result.entities.message == "Projekt zakończony sukcesem"

    def test_parse_body_content_prefix(self) -> None:
        """Conversation follow-up 'Treść:' extracts message without email in text."""
        result = parse_rules("Treść: Projekt idzie zgodnie z planem, raport w załączniku.")
        assert result.entities.message == "Projekt idzie zgodnie z planem, raport w załączniku."
        assert result.entities.language is None

    def test_parse_body_content_prefix_long_form(self) -> None:
        """'Treść wiadomości:' extracts body for multi-turn email dialog."""
        result = parse_rules(
            "Treść wiadomości: W załączeniu podsumowanie tygodnia. "
            "Wszystkie zadania zamknięte na czas."
        )
        assert "podsumowanie tygodnia" in (result.entities.message or "")
        assert result.entities.language is None

    def test_parse_email_offer(self) -> None:
        """Offer phrasing fills subject and default body."""
        result = parse_rules("Maila do klient@firma.pl z nową ofertą")
        assert result.intent.intent == "send_email"
        assert result.entities.to == "klient@firma.pl"
        assert result.entities.subject == "Nowa oferta"
        assert result.entities.message


    def test_parse_slack_with_message(self) -> None:
        """Slack notification extracts message after colon."""
        result = parse_rules("Wyślij powiadomienie na Slack #devops: deploy zakończony")
        assert result.intent.intent == "notify_slack"
        assert result.entities.channel == "#devops"
        assert result.entities.message == "deploy zakończony"

    def test_parse_slack_about_message(self) -> None:
        """'Powiadom #sales o X' extracts message."""
        result = parse_rules("Powiadom kanał #sales o podpisaniu umowy z Beta Corp")
        assert result.intent.intent == "notify_slack"
        assert result.entities.message == "podpisaniu umowy z Beta Corp"


class TestParseNotifyQuality:
    def test_notify_channel_only_maps_incomplete_without_message(self) -> None:
        from app.mapper import map_to_dsl

        result = parse_rules("Powiadom #oncall")
        dialog = map_to_dsl(result)
        assert result.intent.intent == "notify_slack"
        assert dialog.status == "incomplete"
        assert any("message" in f for f in dialog.missing_fields)


# ── Report parsing ───────────────────────────────────────────────


class TestParseReport:
    """Report intent and entity extraction."""

    def test_parse_report_weekly(self) -> None:
        """Weekly sales report in PDF — detects trigger + report_type + format."""
        result = parse_rules("Co tydzień raport sprzedaży w PDF")
        assert result.intent.intent == "generate_report"
        assert result.entities.report_type == "sales"
        assert result.entities.format == "pdf"

    def test_parse_report_hr_xlsx_no_false_system(self) -> None:
        """'w formacie xlsx' must not trigger system_file_list via 'ls' substring."""
        result = parse_rules("Co tydzień raport HR w formacie xlsx")
        assert result.intent.intent == "generate_report"
        assert "system_file_list" not in result.intent.intent
        assert result.entities.format == "xlsx"

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

    def test_parse_report_and_email_wyslij_do(self) -> None:
        """Report + 'wyślij do email' without explicit 'email' keyword."""
        result = parse_rules(
            "Co poniedziałek raport HR w xlsx i wyślij do hr@firma.pl"
        )
        assert result.intent.intent == "report_and_email"
        assert result.entities.report_type == "hr"
        assert result.entities.format == "xlsx"
        assert result.entities.to == "hr@firma.pl"

    def test_parse_report_and_email_do_recipient(self) -> None:
        """Scheduled report delivered to email — 'raport … do user@domain'."""
        result = parse_rules(
            "Pierwszego każdego miesiąca raport finansów PDF do cfo@firma.pl"
        )
        assert result.intent.intent == "report_and_email"
        assert result.entities.report_type == "finance"
        assert result.entities.to == "cfo@firma.pl"

    def test_parse_report_and_email_csv_wyslij_do(self) -> None:
        result = parse_rules(
            "Codziennie o 9:00 raport sprzedaży CSV i wyślij do manager@firma.pl"
        )
        assert result.intent.intent == "report_and_email"
        assert result.entities.report_type == "sales"
        assert result.entities.format == "csv"
        assert result.entities.to == "manager@firma.pl"


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

    def test_parse_system_set_model(self) -> None:
        """Model setting command extracts path and target value."""
        result = parse_rules("ustaw model na gpt-4o")
        assert result.intent.intent == "system_settings_set"
        assert result.entities.setting_path == "llm.model"
        assert result.entities.setting_value == "gpt-4o"

    def test_parse_system_set_mode(self) -> None:
        """Mode setting command extracts nlp.default_mode."""
        result = parse_rules("ustaw tryb rules")
        assert result.intent.intent == "system_settings_set"
        assert result.entities.setting_path == "nlp.default_mode"
        assert result.entities.setting_value == "rules"


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
