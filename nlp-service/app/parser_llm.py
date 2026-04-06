"""
LLM-based NLP parser — wywołuje API (OpenAI / Anthropic / Ollama).

Używa structured output (JSON schema) do wyodrębnienia intent + entities.
NIE generuje DSL — tylko rozumie język naturalny.

Obsługuje 3 providery:
  - OpenAI  (OPENAI_API_KEY)
  - Anthropic (ANTHROPIC_API_KEY)
  - Ollama  (OLLAMA_URL, domyślnie http://ollama:11434)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx

from .schemas import NLPResult, NLPIntent, NLPEntities
from .registry import ACTIONS_REGISTRY

log = logging.getLogger("nlp.llm")


# ── Prompts ───────────────────────────────────────────────────

SYSTEM_PROMPT = """Jesteś silnikiem NLP do automatyzacji procesów biznesowych.

Twoim JEDYNYM zadaniem jest:
1. Rozpoznać INTENT (co użytkownik chce zrobić)
2. Wyodrębnić ENTITIES (parametry)
3. Wskazać MISSING (brakujące wymagane pola)

Zwracaj TYLKO poprawny JSON — bez markdown, bez komentarzy.

Dostępne intenty (akcje):
- send_invoice: faktura (required: amount, to)
- send_email: email (required: to)
- generate_report: raport (required: report_type)
- crm_update: aktualizacja CRM (required: entity)
- notify_slack: powiadomienie Slack (required: channel)
- invoice_and_notify: faktura + Slack
- invoice_and_email: faktura + email
- report_and_email: raport + email
- full_invoice_flow: faktura + email + Slack
- full_report_flow: raport + email + Slack

Schemat entities:
{
  "amount": number | null,
  "currency": string | null,
  "to": string | null,
  "subject": string | null,
  "message": string | null,
  "channel": string | null,
  "report_type": string | null,
  "format": string | null,
  "entity": string | null
}

Schemat odpowiedzi:
{
  "intent": {"intent": "...", "confidence": 0.0-1.0},
  "entities": {...},
  "missing": ["field1", "field2"]
}"""

USER_PROMPT_TEMPLATE = """Przeanalizuj tekst i zwróć JSON:

"{text}"
"""


# ── LLM Caller ────────────────────────────────────────────────


async def parse_llm(text: str) -> NLPResult:
    """Parse text using LLM API."""

    provider = _detect_provider()
    log.info("Using LLM provider: %s", provider)

    try:
        if provider == "anthropic":
            raw = await _call_anthropic(text)
        elif provider == "openai":
            raw = await _call_openai(text)
        elif provider == "ollama":
            raw = await _call_ollama(text)
        else:
            raise RuntimeError(f"No LLM provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_URL.")

        parsed = _parse_json_response(raw)
        return NLPResult(
            intent=NLPIntent(**parsed.get("intent", {"intent": "unknown", "confidence": 0.0})),
            entities=NLPEntities(**parsed.get("entities", {})),
            missing=parsed.get("missing", []),
            raw_text=text,
        )

    except Exception as exc:
        log.exception("LLM parsing failed, returning unknown intent")
        return NLPResult(
            intent=NLPIntent(intent="unknown", confidence=0.0),
            entities=NLPEntities(),
            missing=[],
            raw_text=text,
        )


def _detect_provider() -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("OLLAMA_URL"):
        return "ollama"
    return "none"


async def _call_anthropic(text: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)}
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_openai(text: str) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_ollama(text: str) -> str:
    url = os.getenv("OLLAMA_URL", "http://ollama:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM response (handles markdown fences)."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    return json.loads(cleaned)
