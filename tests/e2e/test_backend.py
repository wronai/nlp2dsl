"""
E2E tests for backend service (http://localhost:8010).

Covers:
  GET  /health
  GET  /workflow/actions
  POST /workflow/from-text
  GET  /workflow/history
  POST /workflow/chat/start
  POST /workflow/chat/message
  GET  /workflow/actions/schema
  GET  /workflow/settings
"""

from __future__ import annotations

import pytest
import httpx


pytestmark = pytest.mark.asyncio


# ── Health ─────────────────────────────────────────────────────

async def test_health(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "backend"


# ── Workflow Actions Registry ──────────────────────────────────

async def test_workflow_actions_list(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/actions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for action in data:
        assert "name" in action
        assert "description" in action


async def test_workflow_actions_contains_send_invoice(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/actions")
    assert r.status_code == 200
    names = [a["name"] for a in r.json()]
    assert "send_invoice" in names


# ── NLP Text → DSL ────────────────────────────────────────────

async def test_from_text_dsl_only_no_execute(backend_client: httpx.AsyncClient):
    r = await backend_client.post("/workflow/from-text", json={
        "text": "Wyślij fakturę na 1500 PLN do klient@firma.pl",
        "mode": "rules",
        "execute": False,
    })
    assert r.status_code in (200, 400, 422)
    if r.status_code == 200:
        data = r.json()
        assert "status" in data
        assert data["status"] in ("complete", "incomplete")


async def test_from_text_empty_returns_400(backend_client: httpx.AsyncClient):
    r = await backend_client.post("/workflow/from-text", json={"text": ""})
    assert r.status_code == 400


async def test_from_text_unknown_intent_propagates_error(backend_client: httpx.AsyncClient):
    r = await backend_client.post("/workflow/from-text", json={
        "text": "asdfjklasdfhkjasdhf",
        "mode": "rules",
        "execute": False,
    })
    assert r.status_code in (400, 422, 503)


# ── Workflow History ───────────────────────────────────────────

async def test_workflow_history_returns_list(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/history")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


async def test_workflow_history_unknown_id_returns_404(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/history/nonexistent-wf-xyz-000")
    assert r.status_code == 404


# ── Chat Proxy (workflow → nlp-service) ───────────────────────

async def test_chat_start_proxied_to_nlp(backend_client: httpx.AsyncClient):
    r = await backend_client.post(
        "/workflow/chat/start",
        json={"text": "Wyślij fakturę"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "conversation_id" in data
    assert "message" in data


async def test_chat_start_empty_returns_error(backend_client: httpx.AsyncClient):
    r = await backend_client.post(
        "/workflow/chat/start",
        json={"text": ""},
    )
    assert r.status_code in (400, 422)


async def test_chat_message_proxied_to_nlp(backend_client: httpx.AsyncClient):
    start = await backend_client.post(
        "/workflow/chat/start",
        json={"text": "Wyślij fakturę"},
    )
    assert start.status_code == 200
    conv_id = start.json()["conversation_id"]

    msg = await backend_client.post(
        "/workflow/chat/message",
        json={"conversation_id": conv_id, "text": "1500 PLN"},
    )
    assert msg.status_code == 200
    data = msg.json()
    assert "message" in data


# ── Actions Schema (proxied) ───────────────────────────────────

async def test_workflow_actions_schema(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/actions/schema")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert len(data) > 0


# ── Settings Proxy ─────────────────────────────────────────────

async def test_workflow_settings_proxied(backend_client: httpx.AsyncClient):
    r = await backend_client.get("/workflow/settings")
    assert r.status_code == 200
    data = r.json()
    assert "settings" in data
