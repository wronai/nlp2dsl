"""Shared print/preview helpers for examples and nlp2dsl-demo CLI."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from .artifacts import ExampleArtifactWriter

import requests

from .artifacts import get_example_writer
from .client import NLP2DSLClient


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def execution_payload(result: Mapping[str, Any]) -> dict[str, Any] | None:
    """Normalize execution block from /workflow/from-text (`result`) or chat (`execution`)."""
    data = result.get("execution") or result.get("result")
    return data if isinstance(data, dict) else None


def print_execution_step_detail(step: Mapping[str, Any]) -> None:
    action = step.get("action", "?")
    step_status = step.get("status", "?")
    icon = "✅" if step_status == "completed" else "❌"
    print(f"  {icon} {action}: {step_status}")
    step_result = step.get("result")
    if isinstance(step_result, dict):
        for key, value in step_result.items():
            if value not in (None, "", {}):
                print(f"      {key}: {value}")
    if step.get("error"):
        print(f"      error: {step['error']}")


def print_run_context_hints(result: Mapping[str, Any]) -> None:
    """Reflection, DOQL autofill, autonomous resolution — invoice validation/generation."""
    reflection = result.get("reflection")
    if isinstance(reflection, dict):
        from .reflection import format_reflection_summary

        print(format_reflection_summary(reflection))

    autofill = result.get("autofill_applied")
    if autofill:
        print(f"✨ Autofill DOQL: {', '.join(str(x) for x in autofill)}")

    auto_steps = result.get("autonomous_steps")
    if auto_steps:
        print(f"🔄 Autonomiczne kroki: {', '.join(str(x) for x in auto_steps)}")

    dsl = result.get("dsl") or {}
    for step in dsl.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = step.get("action", "")
        config = step.get("config") or {}
        attachment = config.get("attachment_path")
        if attachment:
            print(f"📎 Załącznik faktury: {attachment}")
        if action == "generate_invoice":
            print(f"🧾 Generowanie faktury: {config}")


def print_run_outcome(result: Mapping[str, Any], *, query: str | None = None) -> None:
    """Human-readable output for `nlp2dsl run` and examples."""
    if query:
        print(f"🧠 Zapytanie: {query!r}")

    status = result.get("status", "unknown")
    print(f"Status: {status}")

    if status == "incomplete":
        missing = result.get("missing_fields") or result.get("missing") or []
        if missing:
            print(f"❗ Missing: {', '.join(str(m) for m in missing)}")
        prompt = result.get("prompt_user") or result.get("message")
        if prompt:
            print(f"🤖 {prompt}")
        partial = result.get("partial_workflow") or result.get("dsl")
        if partial:
            print("⚠️  Częściowy DSL:")
            print_json(partial)
        print_run_context_hints(result)
        return

    if status == "error":
        print(f"❌ {result.get('error') or result.get('message', 'nieznany błąd')}")
        print_run_context_hints(result)
        return

    print_run_context_hints(result)

    dsl = result.get("dsl")
    if dsl:
        print(f"Workflow: {dsl.get('name', '?')} ({len(dsl.get('steps', []))} kroków)")
        for i, step in enumerate(dsl.get("steps", []), 1):
            if isinstance(step, dict):
                print(f"  {i}. {step.get('action', '')} -> {step.get('config', {})}")

    execution = execution_payload(result)
    if execution:
        print(f"Execution: {execution.get('status', '?')}")
        for step in execution.get("steps") or []:
            if isinstance(step, dict):
                print_execution_step_detail(step)
        wf_id = execution.get("workflow_id")
        if wf_id:
            print(f"  workflow_id: {wf_id}")


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
        execution = execution_payload(result)
        if execution is not None:
            print("✅ Wynik wykonania:")
            print_json(execution)
            print_run_context_hints(result)
            for index, step in enumerate(execution.get("steps") or [], 1):
                if isinstance(step, dict):
                    icon = "✅" if step.get("status") == "completed" else "❌"
                    print(f"   Krok {index} ({step.get('action')}): {icon}")
                    step_result = step.get("result")
                    if isinstance(step_result, dict):
                        for key, value in step_result.items():
                            if value not in (None, "", {}):
                                print(f"      {key}: {value}")
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


def ensure_services(
    client: NLP2DSLClient,
    *,
    timeout_s: float | None = None,
    exit_on_failure: bool | None = None,
) -> bool:
    if client.wait_for_health(timeout_s=timeout_s):
        return True
    timeout = timeout_s
    if timeout is None:
        timeout = float(os.environ.get("NLP2DSL_HEALTH_TIMEOUT", "120"))
    print(
        f"❌ Usługi nlp2dsl nie odpowiadają po {timeout:.0f}s.\n"
        "   Uruchom: docker compose up -d\n"
        f"   Backend: {client.backend_url}/health\n"
        f"   NLP:     {client.nlp_service_url}/health\n"
        f"   Worker:  {client.worker_url}/health"
    )
    if exit_on_failure is None:
        exit_on_failure = os.environ.get("NLP2DSL_ENSURE_SERVICES_NO_EXIT", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        )
    if exit_on_failure:
        raise SystemExit(1)
    return False
