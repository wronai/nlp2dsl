"""
LLM-based NLP parser — via LiteLLM (unified API for 100+ providers).

Używa structured output (JSON schema) do wyodrębnienia intent + entities.
NIE generuje DSL — tylko rozumie język naturalny.

Obsługiwane providery (automatycznie przez LiteLLM):
  - OpenRouter  (OPENROUTER_API_KEY)  → np. openrouter/openai/gpt-5-mini
  - OpenAI      (OPENAI_API_KEY)      → np. gpt-4o-mini
  - Anthropic   (ANTHROPIC_API_KEY)   → np. claude-sonnet-4-20250514
  - Ollama      (OLLAMA_API_BASE)     → np. ollama/llama3
  - Azure, Groq, Together, Mistral, Cohere, Bedrock, ...

Konfiguracja (env vars):
  LLM_MODEL         — model do użycia (default: openrouter/openai/gpt-5-mini)
  LLM_TEMPERATURE   — temperatura (default: 0)
  LLM_MAX_TOKENS    — max tokenów odpowiedzi (default: 1024)
  LLM_API_BASE      — custom API base URL (opcjonalne)

  Klucze API (LiteLLM automatycznie wykrywa):
  OPENROUTER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, itp.
"""

import json
import logging
import os

import litellm
from litellm import acompletion

from app.schemas import NLPEntities, NLPIntent, NLPResult

log = logging.getLogger("nlp.llm")

LLM_RESPONSE_PREVIEW_LEN: int = int("200")

# ── LiteLLM config ───────────────────────────────────────────

litellm.telemetry = False
litellm.drop_params = True

LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/openai/gpt-5-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_API_BASE = os.getenv("LLM_API_BASE", None)


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
- notify_telegram: powiadomienie Telegram (required: chat_id)
- notify_teams: powiadomienie Microsoft Teams (required: channel)
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
  "chat_id": string | null,
  "title": string | null,
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


# ── LLM Caller (LiteLLM) ─────────────────────────────────────


async def parse_llm(text: str) -> NLPResult:
    """Parse text using LLM via LiteLLM."""

    provider = _detect_provider()
    model = LLM_MODEL

    log.info("LLM call: model=%s provider=%s", model, provider)

    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
            ],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
        }

        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = await acompletion(**kwargs)

        raw = response.choices[0].message.content
        log.debug("LLM raw response: %s", raw[:LLM_RESPONSE_PREVIEW_LEN])

        parsed = _parse_json_response(raw)

        return NLPResult(
            intent=NLPIntent(**parsed.get("intent", {"intent": "unknown", "confidence": 0.0})),
            entities=NLPEntities(**parsed.get("entities", {})),
            missing=parsed.get("missing", []),
            raw_text=text,
        )

    except Exception:
        log.exception("LLM parsing failed (model=%s), returning unknown intent", model)
        return NLPResult(
            intent=NLPIntent(intent="unknown", confidence=0.0),
            entities=NLPEntities(),
            missing=[],
            raw_text=text,
        )


def _detect_provider() -> str:
    """Detect which LLM provider is configured."""
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("OLLAMA_API_BASE"):
        return "ollama"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("TOGETHER_API_KEY"):
        return "together"
    if os.getenv("MISTRAL_API_KEY"):
        return "mistral"
    if os.getenv("COHERE_API_KEY"):
        return "cohere"
    if LLM_API_BASE:
        return "custom"
    return "none"


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM response (handles markdown fences)."""
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        cleaned = cleaned[start:end]

    return json.loads(cleaned)
