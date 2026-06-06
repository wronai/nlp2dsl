"""Demonstracja idempotencji side effects — replay bez ponownego wykonania."""

from __future__ import annotations

import os
from typing import Any, Optional

import requests

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services, print_execution_result

IDEMPOTENCY_KEY_BASE = "example-15-invoice-replay"


def _idempotency_key() -> str:
    """Run-scoped key so stale Postgres rows do not 409 when clear endpoint is absent."""
    run_id = os.environ.get("NLP2DSL_RUN_ID", "").strip()
    if run_id:
        return f"{IDEMPOTENCY_KEY_BASE}-{run_id}"
    return IDEMPOTENCY_KEY_BASE


def _try_clear_idempotency(client: NLP2DSLClient) -> None:
    try:
        client.clear_idempotency()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(
                "ℹ️  Backend bez /workflow/idempotency/clear — używam run-scoped idempotency_key",
            )
            return
        raise


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Idempotencja side effects ===\n")

    if not ensure_services(client):
        return {}

    _try_clear_idempotency(client)
    idempotency_key = _idempotency_key()

    text = "Wyślij fakturę na 500 PLN do test@firma.pl"
    print(f"▶ Pierwsze wykonanie (from-text, key={idempotency_key})")
    first = client.workflow_from_text(
        text,
        execute=True,
        mode="rules",
        idempotency_key=idempotency_key,
    )
    if first.get("status") != "executed":
        print(f"⚠️  status={first.get('status')} missing={first.get('missing_fields')}")
        return {"first": first}

    dsl = first.get("dsl")
    if not isinstance(dsl, dict):
        print("⚠️  Brak DSL w odpowiedzi from-text")
        return {"first": first}

    print_execution_result(first.get("result", {}))
    print(f"   idempotent_replay={first.get('idempotent_replay', False)}")

    print(f"\n▶ Drugie wykonanie (ten sam DSL + key — oczekiwany replay)")
    second = client.workflow_execute(
        dsl,
        idempotency_key=idempotency_key,
        skip_policy_check=True,
    )
    print_execution_result(second.get("result", {}))
    replay = bool(second.get("idempotent_replay"))
    print(f"   idempotent_replay={replay}")

    if replay:
        print("\n✅ Replay OK — side effect nie wykonany ponownie")
    else:
        print("\n❌ Brak replay — idempotency store backendu (POSTGRES_URL / ten sam worker)")
        raise SystemExit(1)

    return {"first": first, "second": second, "replay_ok": replay}
