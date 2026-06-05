"""High-level demo helpers built on top of the reusable SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

import requests

from .client import NLP2DSLClient
from .example_loader import load_example_runner
from .preview import (
    ensure_services,
    execute_from_text,
    preview_text_examples,
    print_json,
    print_workflow_preview,
    workflow_http_error_result,
)

CONSTANT_50 = 50
CONSTANT_300 = 300


CODE_PREVIEW_LEN = CONSTANT_300
SECTION_SEPARATOR = "=" * CONSTANT_50


@dataclass(frozen=True)
class DemoSpec:
    """Metadata for a runnable demo exposed by the package CLI."""

    name: str
    description: str
    runner: Callable[[Optional[NLP2DSLClient]], Any]


def _print_code_generation_preview(result: Mapping[str, Any]) -> None:
    language = result.get("language", "unknown")
    code = result.get("code", "")

    print(f"Language: {language}")
    print(f"Code length: {len(code)} characters")

    tests = result.get("tests")
    if tests:
        print(f"Tests included: {len(tests)} characters")

    preview = code[:CODE_PREVIEW_LEN]
    print("\nGenerated code preview:")
    print(f"{preview}..." if len(code) > CODE_PREVIEW_LEN else preview)


def run_crm_update_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Aktualizacja CRM ===\n")

    if not ensure_services(client):
        return {}

    preview_text_examples(client, "", CRM_TEXT_EXAMPLES, finalize_artifacts=False)
    return execute_from_text(client, CRM_TEXT_EXAMPLES[0], label="Wykonywanie z zapytania NLP")


def run_action_catalog_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Katalog Akcji ===\n")

    if not ensure_services(client):
        return {}

    actions = client.workflow_actions()
    results: Dict[str, Any] = {"actions": actions, "schemas": {}, "samples": {}}

    print("🔎 Dynamicznie pobrane akcje i schematy:")
    for action in actions:
        name = action.get("name", "unknown")
        print(f"\n• {name}: {action.get('description', '')}")
        schema = client.workflow_action_schema(name)
        results["schemas"][name] = schema
        print(f"  Schema: {schema.get('config_schema', {})}")

        prompt = ACTION_SAMPLE_PROMPTS.get(name)
        if prompt:
            print(f"  🧠 NLP → DSL → wykonanie: '{prompt}'")
            try:
                sample = client.workflow_from_text(prompt, execute=True, mode="auto")
            except requests.HTTPError as exc:
                sample = workflow_http_error_result(exc)
            results["samples"][name] = sample
            print_workflow_preview(sample)

    return results


def run_automation_gallery_demo(client: Optional[NLP2DSLClient] = None) -> list[dict[str, Any]]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Galeria automatyzacji bez boilerplate ===\n")

    if not ensure_services(client):
        return []

    results: list[dict[str, Any]] = []
    for title, prompt in AUTOMATION_GALLERY_QUERIES:
        print(f"\n📝 {title}")
        result = execute_from_text(client, prompt, label="Wykonywanie z NLP")
        results.append({"title": title, "query": prompt, "result": result})
    return results


DEFAULT_INVOICE_PROMPT = "Wyślij fakturę na 1500 PLN do klient@firma.pl"

CODE_GENERATION_SPECS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "Python NWD",
        "description": "Funkcja obliczająca NWD dwóch liczb (algorytm Euklidesa)",
        "language": "python",
        "context": "Dodaj sprawdzanie typów i dokumentację",
        "include_tests": True,
    },
    {
        "title": "JavaScript bubble sort",
        "description": "Funkcja sortowania bąbelkowego dla tablicy liczb",
        "language": "javascript",
        "context": "Zwracaj nową tablicę bez mutacji",
        "include_tests": False,
    },
    {
        "title": "Go CSV filter",
        "description": "CLI w Go do parsowania CSV i filtrowania po kolumnie",
        "language": "go",
        "context": "Użyj flag i czytelnych komunikatów błędów",
        "include_tests": True,
    },
)

CODE_WORKFLOW_TEXT_EXAMPLES: tuple[str, ...] = (
    "Napisz funkcję w JavaScript do sortowania bąbelkowego",
    "Stwórz API w Pythonie do walidacji maila",
    "Wygeneruj program w Go do liczenia linii w pliku",
)

CODE_WORKER_SPECS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "C++ prime checker",
        "description": "Funkcja sprawdzająca czy liczba jest pierwsza",
        "language": "cpp",
        "include_tests": False,
    },
    {
        "title": "Python Fibonacci",
        "description": "Generator ciągu Fibonacciego",
        "language": "python",
        "include_tests": True,
    },
)

AUTOMATION_GALLERY_QUERIES: tuple[tuple[str, str], ...] = (
    ("Faktura", DEFAULT_INVOICE_PROMPT),
    (
        "Faktura + powiadomienie",
        "Wyślij fakturę na 1500 PLN do klient@firma.pl, email do billing@firma.pl "
        "i powiadom #finance na Slacku",
    ),
    (
        "Aktualizacja CRM",
        "Zaktualizuj CRM dla leada ACME z etapem qualified i ownerem sales",
    ),
    (
        "Raport + email + Slack",
        "Co tydzień generuj raport sprzedaży PDF, wyślij do manager@firma.pl "
        "i powiadom #sales na Slacku",
    ),
    (
        "Powiadomienie Slack",
        "Powiadom #deployments na Slacku: Wdrożenie zakończone powodzeniem.",
    ),
)

CRM_TEXT_EXAMPLES: tuple[str, ...] = (
    "Zaktualizuj CRM dla leada ACME z etapem qualified",
    "Dodaj notatkę do kontaktu klient@firma.pl",
    "Oznacz leada jako nurtured i przypisz ownera sales",
)

ACTION_SAMPLE_PROMPTS: dict[str, str] = {
    "send_invoice": "Wyślij fakturę na 1500 PLN do klient@firma.pl",
    "send_email": "Wyślij email do team@firma.pl z tematem Status projektu",
    "generate_report": "Wygeneruj raport sprzedaży PDF",
    "crm_update": "Zaktualizuj CRM dla leada ACME",
    "notify_slack": "Powiadom zespół na Slacku o wdrożeniu",
}

# Przykłady 01–12: logika w examples/<dir>/scenario.py (demos.py tylko re-eksportuje)
run_invoice_demo = load_example_runner("01-invoice")
run_email_demo = load_example_runner("02-email")
run_report_and_notify_demo = load_example_runner("03-report-and-notify")
run_scheduled_report_demo = load_example_runner("04-scheduled-report")
run_conversation_flow_demo = load_example_runner("05-conversation-flow")
run_interactive_chat_demo = load_example_runner("06-interactive-chat")
run_email_conversation_demo = load_example_runner("07-email-conversation")
run_multi_object_benchmark = load_example_runner("08-multi-object-benchmark")
run_execution_smoke = load_example_runner("09-execution-smoke")
run_llm_benchmark = load_example_runner("10-llm-benchmark")
run_notify_quality_demo = load_example_runner("11-notify-quality")
run_ir_show_demo = load_example_runner("12-ir-show")
run_autonomous_invoice_stack_demo = load_example_runner("13-autonomous-invoice-stack")


def run_code_generation_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Direct Code Generation API ===\n")

    if not ensure_services(client):
        return {}

    results: Dict[str, Any] = {}
    direct_results = _run_direct_code_generation(client)
    results["direct"] = direct_results[0] if direct_results else {}
    results["direct_examples"] = direct_results

    print(f"\n{SECTION_SEPARATOR}\n")

    results["languages"] = _get_supported_languages(client)

    print("\n=== Code Generation via Workflow ===\n")
    workflow_results = _run_workflow_code_examples(client)
    results["workflow_examples"] = workflow_results
    if workflow_results:
        results["workflow"] = workflow_results[0]

    print("\n=== Code Generation via Conversation ===\n")
    conversation_results = _run_conversation_code_example(client)
    results["conversation_start"] = conversation_results.get("start")
    results["conversation_message"] = conversation_results.get("message")

    print("\n=== Code Generation via Worker ===\n")
    worker_results = _run_worker_code_generation(client)
    results["worker"] = worker_results[0] if worker_results else {}
    results["worker_examples"] = worker_results

    return results


def _run_direct_code_generation(client: NLP2DSLClient) -> list[dict[str, Any]]:
    """Run direct code generation examples."""
    direct_results: list[dict[str, Any]] = []
    for spec in CODE_GENERATION_SPECS:
        payload = {key: value for key, value in spec.items() if key != "title"}
        print(f"\n🧠 {spec['title']}")

        try:
            result = client.generate_code(**payload)
            direct_results.append(result)
            print("✅ Code generated successfully")
            _print_code_generation_preview(result)
        except requests.RequestException as error:
            print(f"❌ Cannot connect to nlp-service. Make sure it's running on port 8002")
            failure = {"error": str(error), "title": spec["title"]}
            direct_results.append(failure)

    return direct_results


def _get_supported_languages(client: NLP2DSLClient) -> dict[str, Any]:
    """Get and display supported languages."""
    try:
        supported = client.supported_languages()
        print("Supported languages:")
        for lang, info in supported["info"].items():
            print(f"  - {lang}: {info['extensions'][0]} ({info['style']})")
        return supported
    except requests.RequestException as error:
        print("❌ Cannot connect to nlp-service")
        return {"error": str(error)}


def _run_workflow_code_examples(client: NLP2DSLClient) -> list[dict[str, Any]]:
    """Run code generation via workflow examples."""
    return preview_text_examples(client, "", CODE_WORKFLOW_TEXT_EXAMPLES)


def _run_conversation_code_example(client: NLP2DSLClient) -> dict[str, Any]:
    """Run code generation via conversation example."""
    results: dict[str, Any] = {}
    conversation = client.nlp_chat_start(text="Chcę napisać program w Javie")
    results["start"] = conversation
    conv_id = conversation.get("conversation_id")
    print(f"✅ Conversation started: {conv_id}")
    print(f"Message: {conversation.get('message')}")

    if conversation.get("missing"):
        print(f"Missing fields: {conversation['missing']}")
        continuation = client.nlp_chat_message(
            conv_id,
            "Klasa do obsługi kalkulatora z podstawowymi operacjami",
        )
        results["message"] = continuation
        print(f"\nResponse: {continuation.get('message')}")

        if continuation.get("form"):
            print("Form data:")
            print(json.dumps(continuation["form"], indent=2, ensure_ascii=False))

    return results


def _run_worker_code_generation(client: NLP2DSLClient) -> list[dict[str, Any]]:
    """Run code generation via worker examples."""
    worker_results: list[dict[str, Any]] = []
    for spec in CODE_WORKER_SPECS:
        payload = {key: value for key, value in spec.items() if key != "title"}
        print(f"\n🧠 {spec['title']}")
        worker_result = client.worker_generate_code(**payload)
        worker_results.append(worker_result)

        print("✅ Code generated via worker")
        print(f"Status: {worker_result['status']}")

        if "result" in worker_result:
            generated = worker_result["result"]
            if "error" in generated:
                print(f"❌ Generation error: {generated['error']}")
            else:
                print(f"Language: {generated.get('language')}")
                print(f"Code length: {len(generated.get('code', ''))} characters")

    return worker_results


def list_available_demos() -> tuple[DemoSpec, ...]:
    return DEMO_SPECS


DEMO_SPECS: tuple[DemoSpec, ...] = (
    DemoSpec("invoice", "Wysyłanie faktury", run_invoice_demo),
    DemoSpec("email", "Wysyłanie e-maila", run_email_demo),
    DemoSpec("report", "Raport i powiadomienia", run_report_and_notify_demo),
    DemoSpec("scheduled-report", "Zaplanowane raporty", run_scheduled_report_demo),
    DemoSpec("conversation", "Konwersacyjny flow", run_conversation_flow_demo),
    DemoSpec("interactive-chat", "Interaktywny chat", run_interactive_chat_demo),
    DemoSpec("email-conversation", "E-mail z dialogiem", run_email_conversation_demo),
    DemoSpec("multi-object-benchmark", "Benchmark 20 obiektów", run_multi_object_benchmark),
    DemoSpec("execution-smoke", "Smoke wykonania E2E", run_execution_smoke),
    DemoSpec("llm-benchmark", "Benchmark LLM-only (20 zapytań)", run_llm_benchmark),
    DemoSpec("notify-quality", "Powiadomienia quality+enrich", run_notify_quality_demo),
    DemoSpec("ir-show", "MVP vs IntentIR (nlp2dsl show)", run_ir_show_demo),
    DemoSpec("code-generation", "Generowanie kodu", run_code_generation_demo),
    DemoSpec("crm", "Aktualizacja CRM", run_crm_update_demo),
    DemoSpec("actions", "Dynamiczny katalog akcji", run_action_catalog_demo),
    DemoSpec("gallery", "Galeria automatyzacji bez boilerplate", run_automation_gallery_demo),
)

DEMO_REGISTRY: dict[str, Callable[[Optional[NLP2DSLClient]], Any]] = {spec.name: spec.runner for spec in DEMO_SPECS}
