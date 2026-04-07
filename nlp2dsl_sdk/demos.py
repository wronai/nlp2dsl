"""High-level demo helpers built on top of the reusable SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

import requests

from .client import ConversationFlow, NLP2DSLClient, workflow_step

CODE_PREVIEW_LEN = 300
SECTION_SEPARATOR = "=" * 50


@dataclass(frozen=True)
class DemoSpec:
    """Metadata for a runnable demo exposed by the package CLI."""

    name: str
    description: str
    runner: Callable[[Optional[NLP2DSLClient]], Any]


def _ensure_services(client: NLP2DSLClient) -> bool:
    try:
        client.health()
        return True
    except requests.RequestException:
        print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
        return False


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _print_workflow_preview(result: Mapping[str, Any]) -> None:
    status = result.get("status")

    if status == "complete":
        print("✅ Wygenerowany DSL:")
        _print_json(result["dsl"])
        steps = result["dsl"].get("steps", [])
        print(f"   Liczba kroków: {len(steps)}")
    elif status == "executed":
        print("✅ Wygenerowany DSL:")
        _print_json(result["dsl"])
        steps = result["dsl"].get("steps", [])
        print(f"   Liczba kroków: {len(steps)}")
        if result.get("result") is not None:
            print("✅ Wynik wykonania:")
            _print_json(result["result"])
    else:
        print(f"❌ Workflow nie powiódł się: {result.get('error', 'nieznany błąd')}")


def _print_execution_result(result: Mapping[str, Any]) -> None:
    print("✅ Wynik wykonania:")
    _print_json(result)

    steps = result.get("steps", [])
    if steps:
        print(f"   Liczba kroków: {len(steps)}")
        for index, step in enumerate(steps, 1):
            status = "✅" if step.get("status") == "completed" else "❌"
            print(f"   Krok {index} ({step.get('action')}): {status}")
            if step.get("error"):
                print(f"      Błąd: {step['error']}")


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


def _preview_text_examples(
    client: NLP2DSLClient,
    title: str,
    examples: Sequence[str],
    *,
    execute: bool = False,
) -> list[dict[str, Any]]:
    if title:
        print(title)

    results: list[dict[str, Any]] = []
    for text in examples:
        print(f"\n📝 Przykład: {text}")
        print(f"🧠 Analiza tekstu: '{text}'")
        result = client.workflow_from_text(text, execute=execute)
        results.append(result)
        _print_workflow_preview(result)

    return results


def run_crm_update_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Aktualizacja CRM ===\n")

    if not _ensure_services(client):
        return {}

    _preview_text_examples(client, "", CRM_TEXT_EXAMPLES)

    print("\n📋 Wykonywanie workflow...")
    execution = client.crm_update(
        entity="lead",
        data={"company": "ACME", "status": "qualified", "owner": "sales"},
        name="crm_update_demo",
    )
    _print_execution_result(execution)
    return execution


def run_action_catalog_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Katalog Akcji ===\n")

    if not _ensure_services(client):
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
            print(f"  🧠 Analiza tekstu: '{prompt}'")
            preview = client.workflow_from_text(prompt)
            results["samples"][name] = preview
            _print_workflow_preview(preview)

        runner = ACTION_SAMPLE_RUNNERS.get(name)
        if runner:
            print("  📋 Przykładowe wykonanie:")
            sample = runner(client)
            results["samples"][f"{name}_execution"] = sample
            _print_execution_result(sample)

    return results


def run_automation_gallery_demo(client: Optional[NLP2DSLClient] = None) -> list[dict[str, Any]]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Galeria automatyzacji bez boilerplate ===\n")

    if not _ensure_services(client):
        return []

    return _run_gallery_examples(client, "", AUTOMATION_GALLERY_SPECS)


DEFAULT_INVOICE_PROMPT = "Wyślij fakturę na 1500 PLN do klient@firma.pl"

EMAIL_TEXT_EXAMPLES: tuple[str, ...] = (
    "Wyślij email do team@firma.pl z tematem Status projektu",
    "Napisz do manager@firma.pl: Projekt zakończony sukcesem",
    "Maila do klient@firma.pl z nową ofertą",
    "Przypomnij billing@firma.pl o nieopłaconej fakturze",
)

REPORT_TEXT_EXAMPLES: tuple[str, ...] = (
    "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl",
    "Generuj raport HR i powiadom na #hr",
    "Miesięczny raport finansów do CFO i teamu",
    "Raport kwartalny sprzedaży w CSV i wyślij go do #sales",
)

SCHEDULED_REPORT_SPECS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "daily_sales_report",
        "runner": lambda client: client.create_scheduled_report(
            name="daily_sales_report",
            report_type="sales",
            trigger="daily",
            schedule="09:00",
            email_to="team@firma.pl",
        ),
    },
    {
        "title": "weekly_hr_report",
        "runner": lambda client: client.create_scheduled_report(
            name="weekly_hr_report",
            report_type="hr",
            trigger="weekly",
            schedule="monday 08:00",
            email_to="hr@firma.pl",
            format_type="xlsx",
        ),
    },
    {
        "title": "monthly_finance_report",
        "runner": lambda client: client.create_scheduled_report(
            name="monthly_finance_report",
            report_type="finance",
            trigger="monthly",
            schedule="1st 07:00",
            email_to="cfo@firma.pl",
        ),
    },
    {
        "title": "business_hours_report",
        "runner": lambda client: client.create_scheduled_report(
            name="business_hours_report",
            report_type="sales",
            trigger="daily",
            schedule="09:00",
            email_to="manager@firma.pl",
            format_type="csv",
        ),
    },
)

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

SCHEDULED_REPORT_TEXT_EXAMPLES: tuple[str, ...] = (
    "Codziennie o 9:00 generuj raport sprzedaży",
    "Co poniedziałek raport HR do hr@firma.pl",
    "Pierwszego każdego miesiąca raport finansów",
    "Każdego dnia o 18:00 przygotuj raport sprzedaży dla zespołu",
)

AUTOMATION_GALLERY_SPECS: tuple[Mapping[str, Any], ...] = (
    {
        "title": "Faktura",
        "prompt": DEFAULT_INVOICE_PROMPT,
        "runner": lambda client: client.send_invoice(
            1500.0,
            "klient@firma.pl",
            "PLN",
            name="gallery_invoice_example",
        ),
    },
    {
        "title": "Faktura + powiadomienie",
        "prompt": "Wyślij fakturę i poinformuj księgowość oraz Slack",
        "runner": lambda client: client.send_invoice_and_notify(
            1500.0,
            "klient@firma.pl",
            email_to="billing@firma.pl",
            slack_channel="#finance",
            name="gallery_invoice_notify_example",
        ),
    },
    {
        "title": "Aktualizacja CRM",
        "prompt": "Zaktualizuj CRM dla leada ACME z etapem qualified",
        "runner": lambda client: client.crm_update(
            entity="lead",
            data={"company": "ACME", "status": "qualified", "owner": "sales"},
            name="gallery_crm_update_example",
        ),
    },
    {
        "title": "Raport + email + Slack",
        "prompt": "Co tydzień generuj raport sprzedaży w PDF i wyślij do managera oraz na Slack",
        "runner": lambda client: client.generate_report_and_notify(
            report_type="sales",
            format_type="pdf",
            email_to="manager@firma.pl",
            slack_channel="#sales",
            trigger="weekly",
            name="gallery_report_notify_example",
        ),
    },
    {
        "title": "Powiadomienie Slack",
        "prompt": "Powiadom zespół na Slacku o wdrożeniu",
        "runner": lambda client: client.notify_slack(
            channel="#deployments",
            message="Wdrożenie zakończone powodzeniem.",
            name="gallery_slack_example",
        ),
    },
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

ACTION_SAMPLE_RUNNERS: dict[str, Callable[[NLP2DSLClient], dict[str, Any]]] = {
    "send_invoice": lambda client: client.send_invoice(
        1500.0,
        "klient@firma.pl",
        "PLN",
        name="catalog_invoice_example",
    ),
    "send_email": lambda client: client.send_email(
        "team@firma.pl",
        subject="Status dzienny projektów",
        body="Wszystkie projekty przebiegają zgodnie z harmonogramem.",
        name="catalog_email_example",
    ),
    "generate_report": lambda client: client.generate_report(
        report_type="sales",
        format_type="pdf",
        name="catalog_report_example",
    ),
    "crm_update": lambda client: client.crm_update(
        entity="lead",
        data={"company": "ACME", "status": "qualified", "owner": "sales"},
        name="catalog_crm_example",
    ),
    "notify_slack": lambda client: client.notify_slack(
        channel="#ops",
        message="Automatyczne powiadomienie z katalogu akcji.",
        name="catalog_slack_example",
    ),
}


def _run_workflow_examples(
    client: NLP2DSLClient,
    title: str,
    examples: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if title:
        print(title)

    results: list[dict[str, Any]] = []
    for example in examples:
        print(f"\n📦 {example['title']}")
        result = example["runner"](client)
        results.append(result)
        _print_execution_result(result)

    return results


def _run_gallery_examples(
    client: NLP2DSLClient,
    title: str,
    examples: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if title:
        print(title)

    results: list[dict[str, Any]] = []
    for example in examples:
        print(f"\n📝 {example['title']}")
        prompt = example.get("prompt")
        if prompt:
            print(f"🧠 Analiza tekstu: '{prompt}'")
            preview = client.workflow_from_text(prompt, execute=bool(example.get("execute_preview", False)))
            _print_workflow_preview(preview)
        else:
            preview = {}

        execution = None
        runner = example.get("runner")
        if callable(runner):
            print("\n📋 Wykonywanie workflow...")
            execution = runner(client)
            _print_execution_result(execution)

        results.append({"title": example["title"], "preview": preview, "execution": execution})

    return results


def run_invoice_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie Faktury ===\n")

    if not _ensure_services(client):
        return {}

    _preview_text_examples(client, "", [DEFAULT_INVOICE_PROMPT])

    print("📋 Wykonywanie workflow...")
    execution = client.send_invoice(1500.0, "klient@firma.pl", "PLN")
    _print_execution_result(execution)

    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            print(f"\n🎉 Faktura wysłana! ID: {step['result']['invoice_id']}")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    return execution


def run_email_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Wysyłanie E-maila ===\n")

    if not _ensure_services(client):
        return {}

    _preview_text_examples(client, "", EMAIL_TEXT_EXAMPLES)

    print("\n📋 Wykonywanie workflow...")
    execution = client.send_email(
        to="team@firma.pl",
        subject="Status dzienny projektów",
        body="Wszystkie projekty przebiegają zgodnie z harmonogramem.",
    )

    _print_execution_result(execution)

    if execution.get("status") == "completed":
        step = execution["steps"][0]
        if step.get("status") == "completed":
            print("\n🎉 E-mail wysłany pomyślnie!")
        else:
            print(f"\n❌ Błąd: {step.get('error')}")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    return execution


def run_report_and_notify_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Raport i Powiadomienia ===\n")

    if not _ensure_services(client):
        return {}

    _preview_text_examples(client, "", REPORT_TEXT_EXAMPLES)

    print("\n📋 Wykonywanie workflow z wieloma krokami...")
    execution = client.generate_report_and_notify(
        report_type="sales",
        format_type="pdf",
        email_to="manager@firma.pl",
        slack_channel="#sales",
        trigger="weekly",
    )

    _print_execution_result(execution)

    if execution.get("status") == "completed":
        print("\n🎉 Workflow wykonany pomyślnie!")
    else:
        print(f"\n❌ Workflow nie powiódł się: {execution.get('error')}")

    return execution


def run_scheduled_report_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Przykład: Zaplanowane Raporty ===\n")

    if not _ensure_services(client):
        return {}

    print("📋 Tworzenie raportów z różnymi harmonogramami...\n")
    scheduled_results = _run_workflow_examples(client, "", SCHEDULED_REPORT_SPECS)

    print("\n📝 Przykłady generowania z tekstu:")
    _preview_text_examples(client, "", SCHEDULED_REPORT_TEXT_EXAMPLES)

    last_result = scheduled_results[-1] if scheduled_results else {}

    print("\n🎉 Wszystkie zaplanowane raporty zostały utworzone!")
    print("\n💡 Wskazówka: W systemie produkcyjnym te workflow byłyby uruchamiane")
    print("   automatycznie według zdefiniowanych harmonogramów.")

    return last_result


def run_code_generation_demo(client: Optional[NLP2DSLClient] = None) -> Dict[str, Any]:
    client = client or NLP2DSLClient.from_env()
    print("=== Direct Code Generation API ===\n")

    if not _ensure_services(client):
        return {}

    results: Dict[str, Any] = {}
    direct_results: list[dict[str, Any]] = []
    for index, spec in enumerate(CODE_GENERATION_SPECS, 1):
        payload = {key: value for key, value in spec.items() if key != "title"}
        print(f"\n🧠 {spec['title']}")

        try:
            result = client.generate_code(**payload)
            direct_results.append(result)
            if index == 1:
                results["direct"] = result
            print("✅ Code generated successfully")
            _print_code_generation_preview(result)
        except requests.RequestException as error:
            print(f"❌ Cannot connect to nlp-service. Make sure it's running on port 8002")
            failure = {"error": str(error), "title": spec["title"]}
            direct_results.append(failure)
            if index == 1:
                results["direct"] = failure

    results["direct_examples"] = direct_results

    print(f"\n{SECTION_SEPARATOR}\n")

    try:
        supported = client.supported_languages()
        results["languages"] = supported
        print("Supported languages:")
        for lang, info in supported["info"].items():
            print(f"  - {lang}: {info['extensions'][0]} ({info['style']})")
    except requests.RequestException as error:
        print("❌ Cannot connect to nlp-service")
        results["languages"] = {"error": str(error)}

    print("\n=== Code Generation via Workflow ===\n")
    workflow_results = _preview_text_examples(client, "", CODE_WORKFLOW_TEXT_EXAMPLES)
    results["workflow_examples"] = workflow_results
    if workflow_results:
        results["workflow"] = workflow_results[0]

    print("\n=== Code Generation via Conversation ===\n")
    conversation = client.nlp_chat_start(text="Chcę napisać program w Javie")
    results["conversation_start"] = conversation
    conv_id = conversation.get("conversation_id")
    print(f"✅ Conversation started: {conv_id}")
    print(f"Message: {conversation.get('message')}")

    if conversation.get("missing"):
        print(f"Missing fields: {conversation['missing']}")
        continuation = client.nlp_chat_message(
            conv_id,
            "Klasa do obsługi kalkulatora z podstawowymi operacjami",
        )
        results["conversation_message"] = continuation
        print(f"\nResponse: {continuation.get('message')}")

        if continuation.get("form"):
            print("Form data:")
            print(json.dumps(continuation["form"], indent=2, ensure_ascii=False))

    print("\n=== Code Generation via Worker ===\n")
    worker_results: list[dict[str, Any]] = []
    for index, spec in enumerate(CODE_WORKER_SPECS, 1):
        payload = {key: value for key, value in spec.items() if key != "title"}
        print(f"\n🧠 {spec['title']}")
        worker_result = client.worker_generate_code(**payload)
        worker_results.append(worker_result)
        if index == 1:
            results["worker"] = worker_result

        print("✅ Code generated via worker")
        print(f"Status: {worker_result['status']}")

        if "result" in worker_result:
            generated = worker_result["result"]
            if "error" in generated:
                print(f"❌ Generation error: {generated['error']}")
            else:
                print(f"Language: {generated.get('language')}")
                print(f"Code length: {len(generated.get('code', ''))} characters")

    results["worker_examples"] = worker_results

    return results


def list_available_demos() -> tuple[DemoSpec, ...]:
    return DEMO_SPECS


DEMO_SPECS: tuple[DemoSpec, ...] = (
    DemoSpec("invoice", "Wysyłanie faktury", run_invoice_demo),
    DemoSpec("email", "Wysyłanie e-maila", run_email_demo),
    DemoSpec("report", "Raport i powiadomienia", run_report_and_notify_demo),
    DemoSpec("scheduled-report", "Zaplanowane raporty", run_scheduled_report_demo),
    DemoSpec("conversation", "Konwersacyjny flow", lambda client=None: ConversationFlow(client).run_demo()),
    DemoSpec("code-generation", "Generowanie kodu", run_code_generation_demo),
    DemoSpec("crm", "Aktualizacja CRM", run_crm_update_demo),
    DemoSpec("actions", "Dynamiczny katalog akcji", run_action_catalog_demo),
    DemoSpec("gallery", "Galeria automatyzacji bez boilerplate", run_automation_gallery_demo),
)

DEMO_REGISTRY: dict[str, Callable[[Optional[NLP2DSLClient]], Any]] = {spec.name: spec.runner for spec in DEMO_SPECS}
