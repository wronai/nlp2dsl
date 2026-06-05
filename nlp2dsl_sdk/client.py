"""Reusable HTTP client for the NLP2DSL backend, NLP service and worker."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import requests

DEFAULT_BACKEND_URL = "http://localhost:8010"
DEFAULT_NLP_SERVICE_URL = "http://localhost:8002"
DEFAULT_WORKER_URL = "http://localhost:8004"
DEFAULT_TIMEOUT_SECONDS = 30.0
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_DEFAULT_HTTP_RETRIES = 3


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
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Accept", "application/json; charset=utf-8")
        headers.setdefault("Accept-Charset", "utf-8")
        kwargs["headers"] = headers
        kwargs.setdefault("timeout", self.timeout)

        max_retries = int(os.getenv("NLP2DSL_HTTP_RETRIES", str(_DEFAULT_HTTP_RETRIES)))
        url = f"{base_url}{path}"
        response: requests.Response | None = None

        for attempt in range(max_retries):
            response = self.session.request(method.upper(), url, **kwargs)
            if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == max_retries - 1:
                break
            time.sleep(0.5 * (attempt + 1))

        assert response is not None
        if not response.encoding or response.encoding.lower() in {"ascii", "iso-8859-1"}:
            response.encoding = response.apparent_encoding or "utf-8"
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

    def workflow_history(self, limit: int = 10) -> list[dict[str, Any]]:
        data = self._backend("get", "/workflow/history").json()
        if isinstance(data, list):
            return data[:limit]
        if isinstance(data, dict):
            items = list(data.get("workflows") or data.get("items") or [])
            return items[:limit]
        return []

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
        from .doql_context import load_doql_inline_from_env, resolve_doql_context_path

        inline = load_doql_inline_from_env()
        extra: dict[str, Any] = {}
        if inline:
            extra["context_json"] = json.dumps(inline, ensure_ascii=False)
        doql_path = resolve_doql_context_path()
        if doql_path:
            extra["doql_context_path"] = str(doql_path)
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._backend(
                    "post",
                    "/workflow/chat/start",
                    data={"text": text, **extra},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._backend("post", "/workflow/chat/start", json={"text": text, **extra}).json()

    def chat_message(
        self,
        conversation_id: str,
        text: str,
        audio_path: Optional[str] = None,
        *,
        context_inline: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        from .doql_context import load_doql_inline_from_env, resolve_doql_context_path

        inline = dict(context_inline or {})
        if not inline:
            inline = load_doql_inline_from_env()
        extra: dict[str, Any] = {}
        if inline:
            extra["context_json"] = json.dumps(inline, ensure_ascii=False)
        doql_path = resolve_doql_context_path()
        if doql_path:
            extra["doql_context_path"] = str(doql_path)
        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self._backend(
                    "post",
                    "/workflow/chat/message",
                    data={"conversation_id": conversation_id, "text": text, **extra},
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            return response.json()
        return self._backend(
            "post",
            "/workflow/chat/message",
            json={"conversation_id": conversation_id, "text": text, **extra},
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

    def __init__(self, client: Optional[NLP2DSLClient] = None, *, reflect: bool = False) -> None:
        self.client = client or NLP2DSLClient.from_env()
        self.conversation_id: Optional[str] = None
        self.history: list[dict[str, str]] = []
        self.api_trace: list[dict[str, Any]] = []
        self.reflections: list[dict[str, Any]] = []
        self._reflect = reflect
        self._last_response: dict[str, Any] = {}
        self._turn_index: int = 0
        self._run_id: Optional[str] = None

    def start(self, text: str, audio_path: Optional[str] = None) -> dict[str, Any]:
        import os

        from .artifact_layout import current_run_id, ensure_layout

        example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
        if example_dir:
            ensure_layout(Path(example_dir) / ".nlp2dsl")
            self._run_id = current_run_id(Path(example_dir) / ".nlp2dsl")
        self._turn_index = 0
        print(f"👤 Użytkownik: {text}")

        data = self.client.chat_start(text, audio_path=audio_path)
        self.conversation_id = data["conversation_id"]
        self.history.append({"role": "user", "text": text})
        self._record_turn("user", text, "/workflow/chat/start", data)
        self._handle_response(data)
        return data

    def send_message(
        self,
        text: str,
        audio_path: Optional[str] = None,
        *,
        context_inline: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        print(f"👤 Użytkownik: {text}")

        if not self.conversation_id:
            raise ValueError("Brak ID konwersacji. Najpierw wywołaj start().")

        data = self.client.chat_message(
            self.conversation_id,
            text,
            audio_path=audio_path,
            context_inline=context_inline,
        )
        self.history.append({"role": "user", "text": text})
        self._record_turn("user", text, "/workflow/chat/message", data)
        self._handle_response(data)
        return data

    def _record_turn(
        self,
        role: str,
        text: str,
        endpoint: str,
        response: dict[str, Any],
    ) -> None:
        self._last_response = response
        self.api_trace.append({
            "role": role,
            "text": text,
            "endpoint": endpoint,
            "response": response,
        })

    def save_artifacts(self, artifact_root: Path | str | None = None) -> dict[str, Path]:
        """Write conversation trace + transcript under .nlp2dsl/."""
        import os

        from .conversation_artifacts import write_conversation_artifacts

        root = Path(artifact_root or os.environ.get("NLP2DSL_EXAMPLE_DIR", ".")) / ".nlp2dsl"
        return write_conversation_artifacts(root, self.export_trace())

    def export_trace(self) -> dict[str, Any]:
        """Full dialog trace for TestQL artifacts and docker E2E reports."""
        status = self._last_response.get("status", "unknown")
        return {
            "conversation_id": self.conversation_id,
            "status": status,
            "turns": list(self.api_trace),
            "history": list(self.history),
            "reflections": list(self.reflections),
        }

    def _handle_response(self, data: dict[str, Any]) -> None:
        status = data.get("status")
        message = data.get("message", "")

        if status == "in_progress":
            self._handle_in_progress_response(data, message)
        elif status == "ready":
            self._handle_ready_response(data, message)
        elif status == "completed":
            self._handle_completed_response(data, message)
        elif status == "error":
            self._handle_error_response(message)

        self.history.append({"role": "assistant", "text": message})
        self._refresh_doql_registry(data)
        self._persist_reflection(data)

    def _persist_reflection(self, data: dict[str, Any]) -> None:
        """Store server reflection + optional client-side snapshot."""
        import os

        reflection = data.get("reflection")
        if isinstance(reflection, dict):
            self.reflections.append(reflection)
            if self._reflect:
                from .reflection import format_reflection_summary

                print(format_reflection_summary(reflection) + "\n")

        if not self._reflect:
            return

        example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
        if not example_dir:
            return

        try:
            from .artifact_layout import write_reflection_snapshot
            from .doql_context import resolve_doql_context_path
            from .reflection import reflect_from_doql_path
            from .system_map_bridge import doql_file_to_system_map

            phase = str(data.get("status", "unknown"))
            if isinstance(reflection, dict):
                report_payload = reflection
            else:
                path = resolve_doql_context_path()
                if path is None:
                    return
                report = reflect_from_doql_path(path, data, phase)
                if report is None:
                    return
                report_payload = report.model_dump()
                self.reflections.append(report_payload)

            write_reflection_snapshot(
                Path(example_dir) / ".nlp2dsl",
                turn=self._turn_index,
                phase=phase,
                report=report_payload,
                run_id=self._run_id,
            )
        except OSError:
            pass

    def _refresh_doql_registry(self, data: dict[str, Any]) -> None:
        """Sync environment.doql.less on client after each chat step (source of truth)."""
        try:
            from nlp2dsl_sdk.doql_context import resolve_doql_context_path
            from nlp2dsl_sdk.doql_registry import refresh_doql_registry
        except ImportError:
            return

        path = resolve_doql_context_path()
        if path is None:
            return

        status = str(data.get("status", "unknown"))
        phase = "executed" if status == "executed" else status

        intent: str | None = None
        entities: dict[str, Any] = {}
        dsl = data.get("dsl") or {}
        for step in dsl.get("steps") or []:
            if isinstance(step, dict):
                intent = intent or step.get("action")
                entities.update(step.get("config") or {})

        try:
            registry_path = refresh_doql_registry(
                path,
                intent=intent,
                entities=entities,
                execution=data.get("execution"),
                phase=phase,
            )
        except OSError:
            return

        self._turn_index += 1
        example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
        if example_dir:
            try:
                from .artifact_layout import write_turn_snapshot

                write_turn_snapshot(
                    Path(example_dir) / ".nlp2dsl",
                    turn=self._turn_index,
                    phase=phase,
                    response=data,
                    registry_path=registry_path,
                    run_id=self._run_id,
                )
            except OSError:
                pass

    def _handle_in_progress_response(self, data: dict[str, Any], message: str) -> None:
        """Handle in_progress status response."""
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

        autofill = data.get("autofill_applied")
        if autofill:
            print(f"✨ Uzupełniono z DOQL: {', '.join(autofill)}\n")

    def _handle_ready_response(self, data: dict[str, Any], message: str) -> None:
        """Handle ready status response."""
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

    def _handle_completed_response(self, data: dict[str, Any], message: str) -> None:
        """Handle completed status response."""
        print(f"🤖 System: {message}")
        execution = data.get("execution")
        if execution:
            print("✅ Wynik wykonania:")
            for step in execution.get("steps", []):
                if step.get("status") == "completed":
                    result = step.get("result", {})
                    print(f"   • {step.get('action', '')}: {result}")
            print()

    def _handle_error_response(self, message: str) -> None:
        """Handle error status response."""
        print(f"❌ Błąd: {message}\n")

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
