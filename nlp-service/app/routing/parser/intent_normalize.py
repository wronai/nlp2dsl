"""Post-parse intent normalization — disambiguate LLM/rules edge cases."""

from __future__ import annotations

import re

from app.schemas import NLPIntent, NLPResult

_INVOICE_SEND_PATTERNS = (
    r"\binvoice\s+for\b",
    r"\bsend\s+invoice\b",
    r"\bwyślij\s+faktur",
    r"\bwyslij\s+faktur",
    r"\bwystaw\s+faktur",
    r"\binvoice\s+to\b",
)

_REPORT_DELIVERY_EMAIL_PATTERNS = (
    r"(?:raport|report|zestawienie|sprawozdanie).*?\bdo\s+\S+@\S+",
    r"(?:wyślij|wyslij|prześlij|przeslij|send)\s+do\s+\S+@\S+",
)

_INVOICE_GENERATE_ONLY_PATTERNS = (
    r"\bwygeneruj\s+faktur",
    r"\bwygeneruj\s+plik\s+faktur",
    r"\bgeneruj\s+plik\s+faktur",
    r"\bgenerate\s+invoice\s+file\b",
    r"\bcreate\s+invoice\s+pdf\b",
    r"\bwystaw\s+plik\s+faktur",
)


def normalize_parsed_intent(result: NLPResult) -> NLPResult:
    """Apply deterministic intent fixes without changing entities."""
    intent = result.intent.intent
    text = (result.raw_text or "").lower()

    if intent == "generate_invoice":
        coerced = _coerce_invoice_send(result, text)
        if coerced != intent:
            return result.model_copy(
                update={"intent": NLPIntent(intent=coerced, confidence=result.intent.confidence)}
            )

    if intent == "unknown" and _looks_like_invoice_send(text, result):
        return result.model_copy(
            update={"intent": NLPIntent(intent="send_invoice", confidence=max(0.6, result.intent.confidence))}
        )

    if intent == "generate_report" and _looks_like_report_email_delivery(text, result):
        return result.model_copy(
            update={
                "intent": NLPIntent(
                    intent="report_and_email",
                    confidence=max(0.75, result.intent.confidence),
                )
            }
        )

    return result


def _coerce_invoice_send(result: NLPResult, text: str) -> str:
    if _matches_any(text, _INVOICE_GENERATE_ONLY_PATTERNS):
        return "generate_invoice"
    if _matches_any(text, _INVOICE_SEND_PATTERNS):
        return "send_invoice"
    recipient = result.entities.to or result.entities.email_to
    if recipient and _has_amount_signal(text, result):
        return "send_invoice"
    return "generate_invoice"


def _looks_like_report_email_delivery(text: str, result: NLPResult) -> bool:
    if not (result.entities.to or result.entities.email_to):
        return False
    return _matches_any(text, _REPORT_DELIVERY_EMAIL_PATTERNS)


def _looks_like_invoice_send(text: str, result: NLPResult) -> bool:
    if not (result.entities.to or result.entities.email_to):
        return False
    return _has_amount_signal(text, result) or "faktur" in text or "invoice" in text


def _has_amount_signal(text: str, result: NLPResult) -> bool:
    if result.entities.amount is not None:
        return True
    return bool(re.search(r"\d[\d\s.,]*\s*(pln|usd|eur|gbp|zł)", text, re.IGNORECASE))


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
