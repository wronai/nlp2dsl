"""Quality gate + enrich dla powiadomień Slack/Telegram/Teams."""

from __future__ import annotations

import os
from typing import Any, Optional

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, execute_text_examples, preview_text_examples

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

    print("1️⃣  Analiza (bez wykonania) — pokazuje brakujące pola:\n")
    preview_text_examples(client, "", NOTIFY_EXAMPLES[:1], mode="auto", finalize_artifacts=False)

    print("\n2️⃣  Wykonanie z NLP (execute=true) — complete → worker, incomplete → prompt:\n")
    results = execute_text_examples(
        client,
        "",
        NOTIFY_EXAMPLES,
        mode="auto",
        finalize_artifacts=True,
    )

    executed = sum(1 for r in results if r.get("status") == "executed")
    incomplete = sum(1 for r in results if r.get("status") == "incomplete")
    print(f"\n📊 executed={executed}  incomplete={incomplete}  total={len(results)}")

    return {"results": results, "enrich_enabled": enrich}
