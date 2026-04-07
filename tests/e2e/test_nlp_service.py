"""
E2E tests for nlp-service (http://localhost:8002).

Covers:
  GET  /health
  GET  /nlp/actions
  POST /nlp/parse
  POST /nlp/to-dsl
  POST /chat/start
  POST /chat/message
  GET  /chat/{id}
  GET  /actions/schema
  GET  /settings
"""

from __future__ import annotations

import pytest
import httpx


pytestmark = pytest.mark.asyncio


# ── Health ─────────────────────────────────────────────────────

async def test_health(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "nlp-service"
    assert "actions" in data
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) > 0


# ── NLP Actions Registry ───────────────────────────────────────

async def test_nlp_actions_registry(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/nlp/actions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert len(data) > 0
    for action_name, meta in data.items():
        assert "description" in meta
        assert "required" in meta
        assert "aliases" in meta


# ── NLP Parse ─────────────────────────────────────────────────

async def test_parse_known_intent_rules(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/nlp/parse", json={
        "text": "Wyślij fakturę na 1500 PLN do klient@firma.pl",
        "mode": "rules",
    })
    assert r.status_code == 200
    data = r.json()
    assert "intent" in data
    assert data["intent"]["intent"] != "unknown"
    assert data["intent"]["confidence"] > 0.0
    assert "entities" in data


async def test_parse_unknown_intent_rules(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/nlp/parse", json={
        "text": "asdkfjhaskdfhaksjdhfaksjdhf",
        "mode": "rules",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["intent"]["intent"] == "unknown"


async def test_parse_send_email_intent(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/nlp/parse", json={
        "text": "Wyślij email na adres test@test.pl",
        "mode": "rules",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["intent"]["intent"] != "unknown"


# ── NLP → DSL ─────────────────────────────────────────────────

async def test_to_dsl_complete_invoice(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/nlp/to-dsl", json={
        "text": "Wyślij fakturę na 1500 PLN do klient@firma.pl",
        "mode": "rules",
    })
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        data = r.json()
        assert "status" in data
        assert data["status"] in ("complete", "incomplete")


async def test_to_dsl_unknown_returns_422(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/nlp/to-dsl", json={
        "text": "xyzasdfjklasdf",
        "mode": "rules",
    })
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


# ── Chat / Conversation Loop ───────────────────────────────────

async def test_chat_start_text(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/chat/start", data={"text": "Wyślij fakturę"})
    assert r.status_code == 200
    data = r.json()
    assert "conversation_id" in data
    assert "message" in data
    assert len(data["conversation_id"]) > 0


async def test_chat_start_empty_text_returns_400(nlp_client: httpx.AsyncClient):
    r = await nlp_client.post("/chat/start", data={"text": ""})
    assert r.status_code == 400


async def test_chat_message_continue_conversation(nlp_client: httpx.AsyncClient):
    start = await nlp_client.post("/chat/start", data={"text": "Wyślij fakturę"})
    assert start.status_code == 200
    conv_id = start.json()["conversation_id"]

    msg = await nlp_client.post("/chat/message", data={
        "conversation_id": conv_id,
        "text": "1500 PLN",
    })
    assert msg.status_code == 200
    data = msg.json()
    assert "message" in data
    assert "conversation_id" in data
    assert data["conversation_id"] == conv_id


async def test_chat_state_get(nlp_client: httpx.AsyncClient):
    start = await nlp_client.post("/chat/start", data={"text": "Wyślij email"})
    assert start.status_code == 200
    conv_id = start.json()["conversation_id"]

    state = await nlp_client.get(f"/chat/{conv_id}")
    assert state.status_code == 200
    data = state.json()
    assert "conversation_id" in data or "id" in data


async def test_chat_state_not_found(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/chat/nonexistent-conversation-xyz-000")
    assert r.status_code == 404


# ── Actions Schema ─────────────────────────────────────────────

async def test_actions_schema_all(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/actions/schema")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert len(data) > 0


async def test_action_schema_by_name(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/nlp/actions")
    actions = list(r.json().keys())
    assert len(actions) > 0
    first_action = actions[0]

    schema_r = await nlp_client.get(f"/actions/schema/{first_action}")
    assert schema_r.status_code == 200


async def test_action_schema_unknown_returns_404(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/actions/schema/nonexistent_action_xyz")
    assert r.status_code == 404


# ── Settings ───────────────────────────────────────────────────

async def test_settings_get_all(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/settings")
    assert r.status_code == 200
    data = r.json()
    assert "settings" in data
    assert "schema" in data


async def test_settings_get_llm_section(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/settings/llm")
    assert r.status_code == 200
    data = r.json()
    assert "section" in data
    assert data["section"] == "llm"
    assert "settings" in data


async def test_settings_unknown_section_returns_404(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/settings/nonexistent_section_xyz")
    assert r.status_code == 404


# ── Chat UI HTML ───────────────────────────────────────────────

async def test_chat_ui_serves_html(nlp_client: httpx.AsyncClient):
    r = await nlp_client.get("/chat")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    body = r.text
    assert "NLP2DSL" in body or "voice" in body.lower() or "chat" in body.lower()
