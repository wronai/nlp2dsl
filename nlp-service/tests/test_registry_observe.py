"""HTTP tests for POST /chat/registry/observe."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.conversation.doql_context import load_doql_context
from app.main import app

SAMPLE = """
environment[name="01-invoice"] {}

data {
  send_invoice.amount: 1500;
}

commands[0] {
  name: "send_invoice";
  runtime: "executor:worker";
  required: "amount,to";
}

conversation {
  autofill: true;
}
"""


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_registry_observe_requires_path(client: AsyncClient) -> None:
    resp = await client.post("/chat/registry/observe", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_registry_observe_merges_entities(client: AsyncClient, tmp_path: Path) -> None:
    path = tmp_path / "registry" / "environment.doql.less"
    path.parent.mkdir(parents=True)
    path.write_text(SAMPLE, encoding="utf-8")

    resp = await client.post(
        "/chat/registry/observe",
        json={
            "doql_context_path": str(path),
            "phase": "executed",
            "intent": "send_invoice",
            "entities": {"amount": 2200, "to": "observe@test.pl"},
            "execution": {"status": "completed", "steps": []},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "executed"
    assert Path(data["path"]).is_file()

    ctx = load_doql_context(path)
    assert ctx.data["send_invoice.amount"] == 2200
    assert ctx.data["send_invoice.to"] == "observe@test.pl"
