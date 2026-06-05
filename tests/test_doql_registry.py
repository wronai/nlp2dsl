"""Tests for DOQL registry refresh (live source of truth)."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.doql_context import load_doql_context
from nlp2dsl_sdk.doql_registry import merge_execution_observation, merge_registry_observations, refresh_doql_registry
from nlp2dsl_sdk.system_map_generator import generate_system_map
from nlp2dsl_sdk.system_map_render import render_system_map_doql


def test_refresh_merges_entities(tmp_path: Path) -> None:
    ex = tmp_path / "01-invoice"
    (ex / ".nlp2dsl" / "fixtures").mkdir(parents=True)
    (ex / ".nlp2dsl" / "fixtures" / "invoice-request.txt").write_text(
        "to: test@x.pl\namount: 1500\n", encoding="utf-8"
    )
    ir = generate_system_map(ex, example_id="01-invoice")
    path = ex / ".nlp2dsl" / "environment.doql.less"
    path.write_text(render_system_map_doql(ir), encoding="utf-8")

    refresh_doql_registry(
        path,
        intent="send_invoice",
        entities={"amount": 2000, "to": "nowy@klient.pl"},
        phase="preflight",
    )
    ctx = load_doql_context(path)
    assert ctx.data["send_invoice.amount"] == 2000
    assert ctx.data["send_invoice.to"] == "nowy@klient.pl"
    assert "workflow_history" in path.read_text()


def test_merge_execution_observation_invoice_id() -> None:
    data, history = merge_execution_observation(
        {},
        {},
        {
            "status": "completed",
            "results": [
                {
                    "action": "send_invoice",
                    "output": {"invoice_id": "INV-123"},
                }
            ],
        },
        phase="executed",
    )
    assert data["send_invoice.last_invoice_id"] == "INV-123"
    assert history["last_invoice_id"] == "INV-123"
    assert history["last_status"] == "completed"


def test_merge_registry_observations_preserves_history(tmp_path: Path) -> None:
    ex = tmp_path / "01-invoice"
    (ex / ".nlp2dsl").mkdir(parents=True)
    path = ex / ".nlp2dsl" / "environment.doql.less"
    path.write_text(
        """
environment[name="01-invoice"] {}
data { send_invoice.last_invoice_id: "INV-OLD"; }
workflow_history {
  last_phase: "executed";
  last_invoice_id: "INV-OLD";
  count: 3;
}
conversation { autofill: true; }
""".strip()
        + "\n",
        encoding="utf-8",
    )
    ir = generate_system_map(ex, example_id="01-invoice")
    merge_registry_observations(ir, path)
    assert ir.workflow_history["last_invoice_id"] == "INV-OLD"
    assert ir.workflow_history["last_phase"] == "executed"
    assert ir.data["send_invoice.last_invoice_id"] == "INV-OLD"
