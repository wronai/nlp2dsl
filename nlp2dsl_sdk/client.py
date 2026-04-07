"""Reusable HTTP client for the NLP2DSL backend, NLP service and worker."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import requests

DEFAULT_BACKEND_URL = "http://localhost:8010"
DEFAULT_NLP_SERVICE_URL = "http://localhost:8002"
DEFAULT_WORKER_URL = "http://localhost:8004"
DEFAULT_TIMEOUT_SECONDS = 30.0


def workflow_step(action: str, **config: Any) -> dict[str, Any]:
    """Build a declarative workflow step payload."""

    return {"action": action, "config": dict(config)}


class NLP2DSLClient:
    """Small reusable SDK for the NLP2DSL services."""

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        nlp_service_url: str = DEFAULT_NLP_SERVICE_URL,
        worker_url: str = DEFAULT_WORKER_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.nlp_service_url = nlp_service_url.rstrip("/")
        self.worker_url = worker_url.rstrip("/")
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self._owns_session = session is None

    @classmethod
    def from_env(cls, session: Optional[requests.Session] = None) -> "NLP2DSLClient":
        """Build a client from environment variables used in this repo."""

        backend_url = os.getenv(
            "NLP2DSL_BACKEND_URL",
            os.getenv(
                "BACKEND_URL",
                os.getenv("NLP2DSL_API_URL", DEFAULT_BACKEND_URL),
            ),
        )
        nlp_service_url = os.getenv(
            "NLP2DSL_NLP_SERVICE_URL",
            os.getenv("NLP_SERVICE_URL", DEFAULT_NLP_SERVICE_URL),
        )
        worker_url = os.getenv(
            "NLP2DSL_WORKER_URL",
            os.getenv("WORKER_URL", DEFAULT_WORKER_URL),
        )
        timeout = float(os.getenv("NLP2DSL_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
        return cls(
            backend_url=backend_url,
            nlp_service_url=nlp_service_url,
            worker_url=worker_url,
            timeout=timeout,
            session=session,
        )

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "NLP2DSLClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _request(self, base_url: str, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.request(method.upper(), f"{base_url}{path}", **kwargs)
        response.raise_for_status()
        return response

    def _backend(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return self._request(self.backend_url, method, path, **kwargs)

    def _nlp_service(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return self._request(self.nlp_service_url, method, path, **kwargs)

    def _worker(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return self._request(self.worker_url, method, path, **kwargs)

    def backend_health(self) -> dict[str, Any]:
        return self._backend("get", "/health").json()

    def nlp_service_health(self) -> dict[str, Any]:
        return self._nlp_service("get", "/health").json()

    def worker_health(self) -> dict[str, Any]:
        return self._worker("get", "/health").json()

    def health(self) -> dict[str, Any]:
        return {
            "backend": self.backend_health(),
            "nlp_service": self.nlp_service_health(),
            "worker": self.worker_health(),
        }

    def workflow_from_text(self, text: str, execute: bool = False, mode: str = "auto") -> dict[str, Any]:
        payload = {"text": text, "execute": execute, "mode": mode}
        return self._backend("post", "/workflow/from-text", json=payload).json()

    def run_workflow(
        self,
        name: str,
        steps: Sequence[Mapping[str, Any]],
        trigger: str = "manual",
        schedule: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "trigger": trigger,
            "steps": [dict(step) for step in steps],
        }
        if schedule is not None:
            payload["schedule"] = schedule
        return self._backend("post", "/workflow/run", json=payload).json()

    def workflow_actions(self) -> list[dict[str, Any]]:
        return self._backend("get", "/workflow/actions").json()

    def workflow_action_schema(self, action: Optional[str] = None) -> dict[str, Any]:
        path = "/workflow/actions/schema" if action is None else f"/workflow/actions/schema/{action}"
        return self._backend("get", path).json()

    def settings(self) -> dict[str, Any]:
        return self._backend("get", "/workflow/settings").json()

    def settings_section(self, section: str) -> dict[str, Any]:
        return self._backend("get", f"/workflow/settings/{section}").json()

    def update_settings_section(self, section: str, body: Mapping[str, Any]) -> dict[str, Any]:
        return self._backend("put", f"/workflow/settings/{section}", json=dict(body)).json()

    def set_setting(self, path: str, value: Any) -> dict[str, Any]:
        return self._backend("put", "/workflow/settings", json={"path": path, "value": value}).json()

    def reset_settings(self, body: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        return self._backend("post", "/workflow/settings/reset", json=dict(body or {})).json()

    def chat_start(self, text: str, audio_path: Optional[str] = None) -> dict[str, Any]:
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._backend(
                    "post",
                    "/workflow/chat/start",
                    data={"text": text},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._backend("post", "/workflow/chat/start", json={"text": text}).json()

    def chat_message(
        self,
        conversation_id: str,
        text: str,
        audio_path: Optional[str] = None,
    ) -> dict[str, Any]:
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._backend(
                    "post",
                    "/workflow/chat/message",
                    data={"conversation_id": conversation_id, "text": text},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._backend(
            "post",
            "/workflow/chat/message",
            json={"conversation_id": conversation_id, "text": text},
        ).json()

    def chat_state(self, conversation_id: str) -> dict[str, Any]:
        return self._backend("get", f"/workflow/chat/{conversation_id}").json()

    def nlp_chat_start(self, text: str, audio_path: Optional[str] = None) -> dict[str, Any]:
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._nlp_service(
                    "post",
                    "/chat/start",
                    data={"text": text},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._nlp_service("post", "/chat/start", data={"text": text}).json()

    def nlp_chat_message(
        self,
        conversation_id: str,
        text: str,
        audio_path: Optional[str] = None,
    ) -> dict[str, Any]:
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._nlp_service(
                    "post",
                    "/chat/message",
                    data={"conversation_id": conversation_id, "text": text},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._nlp_service(
            "post",
            "/chat/message",
            data={"conversation_id": conversation_id, "text": text},
        ).json()

    def nlp_chat_state(self, conversation_id: str) -> dict[str, Any]:
        return self._nlp_service("get", f"/chat/{conversation_id}").json()

    def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None,
        include_tests: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "description": description,
            "language": language,
            "context": context,
            "include_tests": include_tests,
        }
        return self._nlp_service("post", "/code/generate", json=payload).json()

    def supported_languages(self) -> dict[str, Any]:
        return self._nlp_service("get", "/code/languages").json()

    def worker_execute(self, action: str, config: Mapping[str, Any], step_id: str = "test-001") -> dict[str, Any]:
        payload = {"step_id": step_id, "action": action, "config": dict(config)}
        return self._worker("post", "/execute", json=payload).json()

    def worker_generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None,
        include_tests: bool = False,
        step_id: str = "test-001",
    ) -> dict[str, Any]:
        return self.worker_execute(
            "generate_code",
            {
                "description": description,
                "language": language,
                "context": context,
                "include_tests": include_tests,
            },
            step_id=step_id,
        )

    def send_invoice(
        self,
        amount: float,
        to: str,
        currency: str = "PLN",
        name: str = "invoice_example",
        trigger: str = "manual",
    ) -> dict[str, Any]:
        return self.run_workflow(
            name=name,
            trigger=trigger,
            steps=[workflow_step("send_invoice", amount=amount, to=to, currency=currency)],
        )

    def send_email(
        self,
        to: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        name: str = "email_example",
        trigger: str = "manual",
    ) -> dict[str, Any]:
        return self.run_workflow(
            name=name,
            trigger=trigger,
            steps=[
                workflow_step(
                    "send_email",
                    to=to,
                    subject=subject or "Automatyczna wiadomość",
                    body=body or "Wiadomość wygenerowana automatycznie.",
                )
            ],
        )

    def generate_report(
        self,
        report_type: str,
        format_type: str = "pdf",
        name: str = "report_example",
        trigger: str = "manual",
    ) -> dict[str, Any]:
        return self.run_workflow(
            name=name,
            trigger=trigger,
            steps=[workflow_step("generate_report", report_type=report_type, format=format_type)],
        )

    def generate_report_and_notify(
        self,
        report_type: str,
        format_type: str = "pdf",
        email_to: Optional[str] = None,
        slack_channel: Optional[str] = None,
        trigger: str = "manual",
        name: Optional[str] = None,
        schedule: Optional[str] = None,
    ) -> dict[str, Any]:
        steps: list[dict[str, Any]] = [
            workflow_step("generate_report", report_type=report_type, format=format_type)
        ]

        if email_to:
            steps.append(
                workflow_step(
                    "send_email",
                    to=email_to,
                    subject=f"Raport {report_type}",
                    body=f"Automatycznie wygenerowany raport {report_type} w formacie {format_type}.",
                )
            )

        if slack_channel:
            steps.append(
                workflow_step(
                    "notify_slack",
                    channel=slack_channel,
                    message=f"📊 Nowy raport {report_type} jest dostępny!",
                )
            )

        return self.run_workflow(
            name=name or f"{report_type}_report_workflow",
            trigger=trigger,
            schedule=schedule,
            steps=steps,
        )

    def create_scheduled_report(
        self,
        name: str,
        report_type: str,
        trigger: str,
        schedule: Optional[str] = None,
        email_to: Optional[str] = None,
        format_type: str = "pdf",
        slack_channel: Optional[str] = None,
    ) -> dict[str, Any]:
        return self.generate_report_and_notify(
            report_type=report_type,
            format_type=format_type,
            email_to=email_to,
            slack_channel=slack_channel,
            trigger=trigger,
            name=name,
            schedule=schedule,
        )

    def notify_slack(
        self,
        channel: str,
        message: Optional[str] = None,
        name: str = "slack_notification_example",
        trigger: str = "manual",
    ) -> dict[str, Any]:
        return self.run_workflow(
            name=name,
            trigger=trigger,
            steps=[
                workflow_step(
                    "notify_slack",
                    channel=channel,
                    message=message or "Automatyczne powiadomienie Slack.",
                )
            ],
        )

    def crm_update(
        self,
        entity: str,
        data: Optional[Mapping[str, Any]] = None,
        name: str = "crm_update_example",
        trigger: str = "manual",
    ) -> dict[str, Any]:
        return self.run_workflow(
            name=name,
            trigger=trigger,
            steps=[workflow_step("crm_update", entity=entity, data=dict(data or {}))],
        )

    def send_invoice_and_notify(
        self,
        amount: float,
        to: str,
        currency: str = "PLN",
        email_to: Optional[str] = None,
        slack_channel: Optional[str] = None,
        trigger: str = "manual",
        name: Optional[str] = None,
    ) -> dict[str, Any]:
        steps: list[dict[str, Any]] = [workflow_step("send_invoice", amount=amount, to=to, currency=currency)]

        if email_to:
            steps.append(
                workflow_step(
                    "send_email",
                    to=email_to,
                    subject=f"Faktura {currency}",
                    body=f"Faktura na kwotę {amount} {currency} została wysłana do {to}.",
                )
            )

        if slack_channel:
            steps.append(
                workflow_step(
                    "notify_slack",
                    channel=slack_channel,
                    message=f"📄 Faktura na kwotę {amount} {currency} została przygotowana.",
                )
            )

        return self.run_workflow(
            name=name or "invoice_notification_workflow",
            trigger=trigger,
            steps=steps,
        )


class ConversationFlow:
    """Convenience helper for the conversational workflow example."""

    def __init__(self, client: Optional[NLP2DSLClient] = None) -> None:
        self.client = client or NLP2DSLClient.from_env()
        self.conversation_id: Optional[str] = None
        self.history: list[dict[str, str]] = []

    def start(self, text: str, audio_path: Optional[str] = None) -> dict[str, Any]:
        print(f"👤 Użytkownik: {text}")

        data = self.client.chat_start(text, audio_path=audio_path)
        self.conversation_id = data["conversation_id"]
        self.history.append({"role": "user", "text": text})
        self._handle_response(data)
        return data

    def send_message(self, text: str, audio_path: Optional[str] = None) -> dict[str, Any]:
        print(f"👤 Użytkownik: {text}")

        if not self.conversation_id:
            raise ValueError("Brak ID konwersacji. Najpierw wywołaj start().")

        data = self.client.chat_message(self.conversation_id, text, audio_path=audio_path)
        self.history.append({"role": "user", "text": text})
        self._handle_response(data)
        return data

    def _handle_response(self, data: dict[str, Any]) -> None:
        status = data.get("status")
        message = data.get("message", "")

        if status == "in_progress":
            print(f"🤖 System: {message}")

            form = data.get("form")
            if form:
                print(f"\n📋 Formularz: {form.get('description', '')}")
                for field in form.get("fields", []):
                    required = "(wymagane)" if field.get("required") else "(opcjonalne)"
                    print(f"   • {field.get('label', field.get('name', ''))}: {field.get('type', '')} {required}")
                    options = field.get("options")
                    if options:
                        print(f"     Opcje: {', '.join(options)}")
                print()

            missing = data.get("missing")
            if missing:
                print(f"❗ Brakuje: {', '.join(missing)}\n")

        elif status == "ready":
            print(f"🤖 System: {message}")
            dsl = data.get("dsl")
            if dsl:
                print(f"📝 Workflow: {dsl['name']} ({len(dsl['steps'])} kroków)")
                for i, step in enumerate(dsl["steps"], 1):
                    config = step.get("config", {})
                    print(f"   Krok {i}: {step.get('action', '')}")
                    for key, value in config.items():
                        print(f"      {key}: {value}")
                print()

        elif status == "completed":
            print(f"🤖 System: {message}")
            execution = data.get("execution")
            if execution:
                print("✅ Wynik wykonania:")
                for step in execution.get("steps", []):
                    if step.get("status") == "completed":
                        result = step.get("result", {})
                        print(f"   • {step.get('action', '')}: {result}")
                print()

        elif status == "error":
            print(f"❌ Błąd: {message}\n")

        self.history.append({"role": "assistant", "text": message})

    def run_demo(self) -> None:
        print("=== Demonstracja Konwersacyjnego Flow ===\n")

        try:
            self.client.health()
        except requests.RequestException:
            print("❌ Nie można połączyć się z API. Uruchom: docker compose up -d")
            return

        print("🚀 Krok 1: Inicjalizacja konwersacji")
        self.start("Chcę wysłać fakturę")

        print("\n📝 Krok 2: Uzupełnienie brakujących danych")
        self.send_message("1500 PLN na klient@firma.pl")

        print("\n⚡ Krok 3: Wykonanie workflow")
        self.send_message("uruchom")

        print("\n📊 Podsumowanie konwersacji:")
        print(f"   ID konwersacji: {self.conversation_id}")
        print(f"   Liczba wiadomości: {len(self.history)}")
        print("   Status: Zakończona sukcesem")

    def run_interactive(self) -> None:
        print("=== Interaktywny Tryb Konwersacji ===")
        print("Wpisz 'quit' aby zakończyć\n")

        while True:
            try:
                text = input("👤 Ty: ").strip()
                if text.lower() in ["quit", "exit", "koniec"]:
                    break

                if not self.conversation_id:
                    self.start(text)
                else:
                    self.send_message(text)

            except KeyboardInterrupt:
                print("\n👋 Do widzenia!")
                break
            except Exception as error:
                print(f"❌ Błąd: {error}")
