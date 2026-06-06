"""Tests for intent normalization."""

from __future__ import annotations

from app.routing.parser.intent_normalize import normalize_parsed_intent
from app.schemas import NLPEntities, NLPIntent, NLPResult


def test_coerce_invoice_for_to_send() -> None:
    result = NLPResult(
        intent=NLPIntent(intent="generate_invoice", confidence=0.9),
        entities=NLPEntities(amount=890.0, currency="USD", to="billing@corp.com"),
        raw_text="Invoice for 890 USD to billing@corp.com",
    )
    normalized = normalize_parsed_intent(result)
    assert normalized.intent.intent == "send_invoice"


def test_keep_generate_when_explicit_file_only() -> None:
    result = NLPResult(
        intent=NLPIntent(intent="generate_invoice", confidence=0.9),
        entities=NLPEntities(amount=890.0, to="billing@corp.com"),
        raw_text="Wygeneruj plik faktury PDF na 890 USD",
    )
    normalized = normalize_parsed_intent(result)
    assert normalized.intent.intent == "generate_invoice"


def test_unknown_amount_email_to_send_invoice() -> None:
    result = NLPResult(
        intent=NLPIntent(intent="unknown", confidence=0.3),
        entities=NLPEntities(amount=1500.0, currency="PLN", to="klient@firma.pl"),
        raw_text="1500 PLN na klient@firma.pl",
    )
    normalized = normalize_parsed_intent(result)
    assert normalized.intent.intent == "send_invoice"


def test_coerce_report_delivery_to_report_and_email() -> None:
    result = NLPResult(
        intent=NLPIntent(intent="generate_report", confidence=0.85),
        entities=NLPEntities(report_type="finance", format="pdf", to="cfo@firma.pl"),
        raw_text="Pierwszego każdego miesiąca raport finansów PDF do cfo@firma.pl",
    )
    normalized = normalize_parsed_intent(result)
    assert normalized.intent.intent == "report_and_email"
