"""Shared print/preview helpers for examples and nlp2dsl-demo CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from .artifacts import ExampleArtifactWriter

import requests

from .artifacts import get_example_writer
from .client import NLP2DSLClient


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def print_workflow_preview(result: Mapping[str, Any]) -> None:
    status = result.get("status")

    if status == "complete":
        print("✅ Wygenerowany DSL:")
        print_json(result["dsl"])
        steps = result["dsl"].get("steps", [])
        print(f"   Liczba kroków: {len(steps)}")
    elif status == "executed":
        print("✅ Wygenerowany DSL:")
        print_json(result["dsl"])
        steps = result["dsl"].get("steps", [])
        print(f"   Liczba kroków: {len(steps)}")
        if result.get("result") is not None:
            print("✅ Wynik wykonania:")
            print_json(result["result"])
    elif status == "incomplete":
        partial = result.get("partial_workflow") or result.get("dsl")
        if partial:
            print("⚠️  Częściowy DSL (brakuje pól):")
            print_json(partial)
        missing = result.get("missing_fields") or []
        if missing:
            print(f"   Brakuje: {', '.join(missing)}")
        prompt = result.get("prompt_user")
        if prompt:
            print(f"   💬 {prompt}")
    elif status == "error":
        print(f"❌ Workflow nie powiódł się: {result.get('error', 'nieznany błąd')}")
    else:
        print(f"❌ Workflow nie powiódł się: {result.get('error', 'nieznany błąd')}")


def print_execution_result(result: Mapping[str, Any]) -> None:
    print("✅ Wynik wykonania:")
    print_json(result)

    steps = result.get("steps", [])
    if steps:
        print(f"   Liczba kroków: {len(steps)}")
        for index, step in enumerate(steps, 1):
            status = "✅" if step.get("status") == "completed" else "❌"
            print(f"   Krok {index} ({step.get('action')}): {status}")
            if step.get("error"):
                print(f"      Błąd: {step['error']}")


def workflow_http_error_result(exc: requests.HTTPError) -> dict[str, Any]:
    response = exc.response
    status = response.status_code if response is not None else None
    detail: Any = None
    if response is not None:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text

    if status == 422:
        message = "Nie rozpoznano intencji"
        if isinstance(detail, dict):
            inner = detail.get("detail", detail)
            if isinstance(inner, dict):
                message = str(inner.get("error") or inner.get("hint") or message)
            else:
                message = str(inner)
        return {"status": "error", "error": message, "http_status": status, "detail": detail}

    message = str(exc)
    if isinstance(detail, dict):
        message = str(detail.get("detail", detail))
    elif detail:
        message = str(detail)
    return {"status": "error", "error": message, "http_status": status, "detail": detail}


def preview_text_examples(
    client: NLP2DSLClient,
    title: str,
    examples: Sequence[str],
    *,
    execute: bool = False,
    mode: str = "auto",
    artifact_writer: ExampleArtifactWriter | None = None,
    finalize_artifacts: bool = True,
) -> list[dict[str, Any]]:
    if title:
        print(title)

    writer = artifact_writer or get_example_writer()
    results: list[dict[str, Any]] = []
    for text in examples:
        print(f"\n📝 Przykład: {text}")
        print(f"🧠 Analiza tekstu: '{text}'")
        try:
            result = client.workflow_from_text(text, execute=execute, mode=mode)
        except requests.HTTPError as exc:
            result = workflow_http_error_result(exc)
            results.append(result)
            print_workflow_preview(result)
            if writer:
                writer.record(text, result, mode=mode)
            continue
        results.append(result)
        print_workflow_preview(result)
        if writer:
            writer.record(text, result, mode=mode)

    if writer and finalize_artifacts:
        writer.finalize(client)

    return results


def execute_from_text(
    client: NLP2DSLClient,
    text: str,
    *,
    mode: str = "auto",
    label: str = "Wykonywanie workflow",
) -> dict[str, Any]:
    """NLP query → DSL → execution (no hardcoded run_workflow helpers)."""
    if label:
        print(f"\n📋 {label}...")
    print(f"🧠 Zapytanie: '{text}'")
    try:
        result = client.workflow_from_text(text, execute=True, mode=mode)
    except requests.HTTPError as exc:
        result = workflow_http_error_result(exc)
        print_workflow_preview(result)
        return result

    print_workflow_preview(result)
    if result.get("status") == "executed" and result.get("result"):
        steps = result["result"].get("steps", [])
        if steps:
            print(f"   Liczba kroków: {len(steps)}")
            for index, step in enumerate(steps, 1):
                icon = "✅" if step.get("status") == "completed" else "❌"
                print(f"   Krok {index} ({step.get('action')}): {icon}")
    return result


def execute_text_examples(
    client: NLP2DSLClient,
    title: str,
    examples: Sequence[str],
    *,
    mode: str = "auto",
    artifact_writer: ExampleArtifactWriter | None = None,
    finalize_artifacts: bool = True,
) -> list[dict[str, Any]]:
    """Run each NL query with execute=True; incomplete queries surface missing_fields."""
    if title:
        print(title)

    writer = artifact_writer or get_example_writer()
    results: list[dict[str, Any]] = []
    for text in examples:
        print(f"\n📝 Zapytanie: {text}")
        try:
            result = client.workflow_from_text(text, execute=True, mode=mode)
        except requests.HTTPError as exc:
            result = workflow_http_error_result(exc)
        results.append(result)
        print_workflow_preview(result)
        if writer:
            writer.record(text, result, mode=mode)

    if writer and finalize_artifacts:
        writer.finalize(client)

    return results


def finalize_example_artifacts(client: NLP2DSLClient | None = None) -> None:
    """Flush .nlp2dsl/ when scenario recorded queries with finalize_artifacts=False."""
    writer = get_example_writer()
    if writer:
        writer.finalize(client)


def ensure_services(client: NLP2DSLClient) -> bool:
    try:
        client.health()
        return True
    except requests.RequestException:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        return False
