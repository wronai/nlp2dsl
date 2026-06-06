"""Parser mode resolution — rules / llm / auto with fallbacks."""

from __future__ import annotations

import logging
import os

from app.routing.parser.intent_normalize import normalize_parsed_intent
from app.routing.parser.llm import _detect_provider, parse_llm
from app.routing.parser.rules import parse_rules
from app.schemas import NLPResult

log = logging.getLogger("nlp.parser")

_FALLBACK_THRESHOLD = float(os.getenv("LLM_FALLBACK_THRESHOLD", "0.5"))


async def parse_with_mode(
    text: str,
    mode: str,
    *,
    confidence_min: float | None = None,
) -> NLPResult:
    mode = mode.lower().strip()
    threshold = confidence_min if confidence_min is not None else _FALLBACK_THRESHOLD

    if mode == "rules":
        return normalize_parsed_intent(parse_rules(text))

    if mode == "llm":
        if _detect_provider() == "none":
            return normalize_parsed_intent(parse_rules(text))
        llm_result = normalize_parsed_intent(await parse_llm(text))
        if llm_result.intent.intent != "unknown":
            return llm_result
        rules_result = normalize_parsed_intent(parse_rules(text))
        if rules_result.intent.intent != "unknown":
            log.info("LLM returned unknown; using rules fallback")
            return rules_result
        return llm_result

    # auto
    rules_result = normalize_parsed_intent(parse_rules(text))
    if rules_result.intent.confidence >= threshold:
        return rules_result
    if _detect_provider() == "none":
        return rules_result
    try:
        llm_result = normalize_parsed_intent(await parse_llm(text))
        if llm_result.intent.confidence > rules_result.intent.confidence:
            return llm_result
    except Exception:
        log.exception("LLM fallback failed in auto mode")
    return rules_result
