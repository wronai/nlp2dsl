"""Benchmark 20 zapytań wyłącznie w trybie LLM (OpenRouter)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import importlib.util

BENCH_DIR = Path(__file__).resolve().parent.parent / "08-multi-object-benchmark"
_bench_spec = importlib.util.spec_from_file_location("bench08_scenario", BENCH_DIR / "scenario.py")
_bench_mod = importlib.util.module_from_spec(_bench_spec)
assert _bench_spec.loader is not None
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))
_bench_spec.loader.exec_module(_bench_mod)
run_benchmark = _bench_mod.run_benchmark

from nlp2dsl_sdk.client import NLP2DSLClient
from nlp2dsl_sdk.preview import ensure_services


def run(client: Optional[NLP2DSLClient] = None) -> dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Benchmark LLM-only (OpenRouter) ===\n")
    print("Wymaga: OPENROUTER_API_KEY w .env + docker compose up nlp-service\n")

    if not ensure_services(client):
        return {}

    health = client.nlp_service_health()
    print(f"Provider: {health.get('llm_provider')}  Model: {health.get('llm_model')}\n")

    # Dłuższy timeout — każde zapytanie może wołać LLM
    client.timeout = max(client.timeout, 90.0)
    return run_benchmark(client, mode="llm", verbose=True)
