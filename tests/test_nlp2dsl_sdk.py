"""Contract tests for the reusable NLP2DSL SDK."""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from nlp2dsl_sdk import NLP2DSLClient, workflow_step


class DummyResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False)
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._payload


class DummySession:
    def __init__(self, responses: list[DummyResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> DummyResponse:
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError(f"No more stub responses for {method} {url}")
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def client_factory() -> Any:
    def _factory(*responses: DummyResponse) -> tuple[NLP2DSLClient, DummySession]:
        session = DummySession(list(responses))
        client = NLP2DSLClient(
            backend_url="http://backend.test",
            nlp_service_url="http://nlp.test",
            worker_url="http://worker.test",
            session=session,
        )
        return client, session

    return _factory


def test_from_env_prefers_repo_env_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_URL", "http://backend.env")
    monkeypatch.setenv("NLP_SERVICE_URL", "http://nlp.env")
    monkeypatch.setenv("WORKER_URL", "http://worker.env")
    monkeypatch.setenv("NLP2DSL_TIMEOUT", "12.5")

    client = NLP2DSLClient.from_env(session=DummySession([]))

    assert client.backend_url == "http://backend.env"
    assert client.nlp_service_url == "http://nlp.env"
    assert client.worker_url == "http://worker.env"
    assert client.timeout == 12.5


def test_workflow_and_conversation_endpoints(client_factory: Any) -> None:
    client, session = client_factory(
        DummyResponse({"status": "complete", "dsl": {"name": "demo"}}),
        DummyResponse({"workflow_id": "wf-1", "status": "completed", "steps": []}),
        DummyResponse({"conversation_id": "conv-1", "status": "in_progress"}),
        DummyResponse({"conversation_id": "conv-1", "status": "ready", "dsl": {"name": "auto_send_invoice"}}),
        DummyResponse({"action": "send_invoice", "fields": [{"name": "to"}]}),
    )

    generated = client.workflow_from_text("Wyślij fakturę", execute=False)
    assert generated["status"] == "complete"

    execution = client.send_invoice(1500.0, "klient@firma.pl")
    assert execution["status"] == "completed"

    start = client.chat_start("Chcę wysłać fakturę")
    assert start["conversation_id"] == "conv-1"

    message = client.chat_message("conv-1", "1500 PLN")
    assert message["conversation_id"] == "conv-1"

    schema = client.workflow_action_schema("send_invoice")
    assert schema["action"] == "send_invoice"
    assert schema["fields"][0]["name"] == "to"

    assert session.calls[0][1] == "http://backend.test/workflow/from-text"
    assert session.calls[0][2]["json"] == {"text": "Wyślij fakturę", "execute": False, "mode": "auto"}

    assert session.calls[1][1] == "http://backend.test/workflow/run"
    assert session.calls[1][2]["json"]["steps"][0]["config"]["amount"] == 1500.0
    assert session.calls[1][2]["json"]["steps"][0]["config"]["to"] == "klient@firma.pl"

    assert session.calls[2][1] == "http://backend.test/workflow/chat/start"
    assert session.calls[2][2]["json"] == {"text": "Chcę wysłać fakturę"}

    assert session.calls[3][1] == "http://backend.test/workflow/chat/message"
    assert session.calls[3][2]["json"] == {"conversation_id": "conv-1", "text": "1500 PLN"}

    assert session.calls[4][1] == "http://backend.test/workflow/actions/schema/send_invoice"


def test_report_helpers_use_report_type_and_schedule(client_factory: Any) -> None:
    client, session = client_factory(
        DummyResponse({"workflow_id": "report-1", "status": "completed", "steps": []}),
        DummyResponse({"workflow_id": "report-2", "status": "completed", "steps": []}),
    )

    client.generate_report_and_notify(
        report_type="sales",
        format_type="pdf",
        email_to="manager@firma.pl",
        slack_channel="#sales",
        trigger="weekly",
        schedule="monday 08:00",
    )

    client.create_scheduled_report(
        name="weekly_hr_report",
        report_type="hr",
        trigger="weekly",
        schedule="monday 08:00",
        email_to="hr@firma.pl",
        format_type="xlsx",
    )

    first_payload = session.calls[0][2]["json"]
    assert first_payload["name"] == "sales_report_workflow"
    assert first_payload["schedule"] == "monday 08:00"
    assert first_payload["steps"][0]["config"]["report_type"] == "sales"
    assert first_payload["steps"][1]["config"]["to"] == "manager@firma.pl"
    assert first_payload["steps"][2]["config"]["channel"] == "#sales"

    second_payload = session.calls[1][2]["json"]
    assert second_payload["name"] == "weekly_hr_report"
    assert second_payload["steps"][0]["config"]["report_type"] == "hr"
    assert second_payload["steps"][0]["config"]["format"] == "xlsx"
    assert second_payload["steps"][1]["config"]["subject"] == "Raport hr"


def test_new_workflow_helpers_are_data_driven(client_factory: Any) -> None:
    assert workflow_step("notify_slack", channel="#ops", message="Deploy done") == {
        "action": "notify_slack",
        "config": {"channel": "#ops", "message": "Deploy done"},
    }

    client, session = client_factory(
        DummyResponse({"workflow_id": "crm-1", "status": "completed", "steps": []}),
        DummyResponse({"workflow_id": "slack-1", "status": "completed", "steps": []}),
        DummyResponse({"workflow_id": "invoice-1", "status": "completed", "steps": []}),
    )

    crm_result = client.crm_update(
        entity="lead",
        data={"status": "qualified", "owner": "sales"},
        name="crm_update_example",
    )
    slack_result = client.notify_slack(
        channel="#ops",
        message="Deploy done",
        name="slack_notification_example",
    )
    invoice_result = client.send_invoice_and_notify(
        1500.0,
        "klient@firma.pl",
        email_to="billing@firma.pl",
        slack_channel="#finance",
        name="invoice_notification_workflow",
    )

    assert crm_result["status"] == "completed"
    assert slack_result["status"] == "completed"
    assert invoice_result["status"] == "completed"

    assert session.calls[0][1] == "http://backend.test/workflow/run"
    assert session.calls[0][2]["json"]["steps"][0]["action"] == "crm_update"
    assert session.calls[0][2]["json"]["steps"][0]["config"]["entity"] == "lead"

    assert session.calls[1][2]["json"]["steps"][0]["action"] == "notify_slack"
    assert session.calls[1][2]["json"]["steps"][0]["config"]["channel"] == "#ops"

    invoice_payload = session.calls[2][2]["json"]
    assert invoice_payload["name"] == "invoice_notification_workflow"
    assert [step["action"] for step in invoice_payload["steps"]] == [
        "send_invoice",
        "send_email",
        "notify_slack",
    ]
    assert invoice_payload["steps"][1]["config"]["to"] == "billing@firma.pl"
    assert invoice_payload["steps"][2]["config"]["channel"] == "#finance"


def test_code_generation_methods_hit_expected_services(client_factory: Any) -> None:
    client, session = client_factory(
        DummyResponse({"language": "python", "code": "print(1)", "tests": ""}),
        DummyResponse({"info": {"python": {"extensions": [".py"], "style": "clean"}}}),
        DummyResponse({"conversation_id": "conv-2", "status": "in_progress"}),
        DummyResponse({"conversation_id": "conv-2", "status": "ready", "form": {"description": "Formularz", "fields": []}}),
        DummyResponse({"step_id": "test-001", "status": "completed", "result": {"language": "cpp"}}),
    )

    direct = client.generate_code(
        description="Funkcja zwracająca 1",
        language="python",
        include_tests=True,
    )
    assert direct["language"] == "python"

    supported = client.supported_languages()
    assert "python" in supported["info"]

    conversation = client.nlp_chat_start("Chcę napisać program w Javie")
    assert conversation["conversation_id"] == "conv-2"

    continuation = client.nlp_chat_message("conv-2", "Klasa do obsługi kalkulatora")
    assert continuation["conversation_id"] == "conv-2"

    worker = client.worker_generate_code("Funkcja zwracająca 1", language="cpp")
    assert worker["status"] == "completed"

    assert session.calls[0][1] == "http://nlp.test/code/generate"
    assert session.calls[0][2]["json"]["include_tests"] is True
    assert session.calls[1][1] == "http://nlp.test/code/languages"
    assert session.calls[2][1] == "http://nlp.test/chat/start"
    assert session.calls[2][2]["data"] == {"text": "Chcę napisać program w Javie"}
    assert session.calls[3][1] == "http://nlp.test/chat/message"
    assert session.calls[3][2]["data"] == {"conversation_id": "conv-2", "text": "Klasa do obsługi kalkulatora"}
    assert session.calls[4][1] == "http://worker.test/execute"
    assert session.calls[4][2]["json"]["action"] == "generate_code"
    assert session.calls[4][2]["json"]["config"]["language"] == "cpp"


def test_health_queries_all_services(client_factory: Any) -> None:
    client, session = client_factory(
        DummyResponse({"status": "ok", "service": "backend"}),
        DummyResponse({"status": "ok", "service": "nlp-service"}),
        DummyResponse({"status": "ok", "service": "worker"}),
    )

    health = client.health()
    assert health["backend"]["service"] == "backend"
    assert health["nlp_service"]["service"] == "nlp-service"
    assert health["worker"]["service"] == "worker"
    assert session.calls[0][1] == "http://backend.test/health"
    assert session.calls[1][1] == "http://nlp.test/health"
    assert session.calls[2][1] == "http://worker.test/health"
