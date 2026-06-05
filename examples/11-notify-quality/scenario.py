"""Quality gate + enrich dla powiadomień Slack/Telegram/Teams."""

from __future__ import annotations

import os
from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, preview_text_examples

NOTIFY_EXAMPLES: tuple[str, ...] = (
    "Powiadom #oncall",
    "Wyślij powiadomienie na Slack #devops: deploy zakończony",
    "Powiadom kanał #sales o podpisaniu umowy z Beta Corp",
    "Notify Telegram chat -1001234567890: API timeout na produkcji",
)


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Powiadomienia: quality_required message ===\n")

    if not ensure_services(client):
        return {}

    enrich = os.getenv("NLP_ENRICH_MISSING", "0")
    print(f"NLP_ENRICH_MISSING={enrich}")
    if enrich in ("1", "true", "yes"):
        print("   (pierwszy przykład bez treści może być uzupełniony przez LLM)\n")
    else:
        print("   (pierwszy przykład bez treści → incomplete; włącz enrich w .env)\n")

    results = preview_text_examples(client, "", NOTIFY_EXAMPLES, mode="auto")
    return {"results": results, "enrich_enabled": enrich}
