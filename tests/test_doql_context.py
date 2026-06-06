"""Tests for SDK DOQL context loading."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.doql_context import DoqlArtifact, DoqlTaskContext, autofill_entities, load_doql_context


def test_load_doql_context_all_supported_blocks(tmp_path: Path) -> None:
    path = tmp_path / "environment.doql.less"
    path.write_text(
        """
// DOQL system map — 01-invoice
// generated: 2026-06-06T08:00:00+00:00

environment[name="01-invoice"] {
  NLP2DSL_BACKEND_URL: "http://localhost:8010";
}

data {
  send_invoice.amount: 1500;
  send_invoice.to: "klient@firma.pl";
}

conversation {
  autofill: false;
  sync_auto_execute: true;
  attachment_required: true;
  generate_invoice_if_missing: false;
  strict_pdf: true;
}

capabilities {
  actions: "send_invoice,mullm_shell_task";
}

workflow_history {
  count: 2;
  last_status: "completed";
}

process {
  mode: "deterministic";
  nlp_parser: "rules_first";
  nlp_confidence_min: 0.75;
  nlp_enrich_missing: true;
  llm_reasoning: "deep";
  llm_temperature: 0.1;
  autonomous: false;
  autonomous_max_rounds: 3;
  ask_user: "never";
  intract_gate: true;
  intract_enforce_clarification: true;
}

process_access {
  agent: "user";
  allow_areas: "files:project";
  deny_areas: "mullm:rag,docker:local";
}

paths {
  read: "fixtures/**";
  write: "generated/**";
}

artifacts[0] {
  path: "fixtures/invoice-request.txt";
  kind: "metadata";
  to: "klient@firma.pl";
  amount: 1500;
}

commands[0] {
  name: "send_invoice";
  required: "amount,to";
  optional: "currency,attachment_path";
  runtime: "executor:worker";
}

resources[0] {
  id: "mullm:rag";
  title: "Mullm workspace";
  connector: "mullm";
  uri_patterns: "mullm://**";
}

access[0] {
  agent: "user";
  resource_area: "mullm:rag";
  actions: "read";
  effect: "deny";
}

runtimes[0] {
  id: "executor:worker";
  kind: "worker";
  status: "available";
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    ctx = load_doql_context(path)

    assert ctx.example_name == "01-invoice"
    assert ctx.generated_at == "2026-06-06T08:00:00+00:00"
    assert ctx.environment["NLP2DSL_BACKEND_URL"] == "http://localhost:8010"
    assert ctx.data["send_invoice.amount"] == 1500
    assert ctx.autofill is False
    assert ctx.sync_auto_execute is True
    assert ctx.attachment_required is True
    assert ctx.generate_invoice_if_missing is False
    assert ctx.strict_pdf is True
    assert ctx.capabilities == ["send_invoice", "mullm_shell_task"]
    assert ctx.workflow_history == {"count": 2, "last_status": "completed"}
    assert ctx.process.mode == "deterministic"
    assert ctx.process.nlp_parser == "rules_first"
    assert ctx.process.nlp_confidence_min == 0.75
    assert ctx.process.nlp_enrich_missing is True
    assert ctx.process.llm_reasoning == "deep"
    assert ctx.process.llm_temperature == 0.1
    assert ctx.process.autonomous_enabled is False
    assert ctx.process.autonomous_max_rounds == 3
    assert ctx.process.ask_user == "never"
    assert ctx.process.intract_gate is True
    assert ctx.process.intract_enforce_clarification is True
    assert ctx.process.agent == "user"
    assert ctx.process.allow_resource_areas == ["files:project"]
    assert ctx.process.deny_resource_areas == ["mullm:rag", "docker:local"]
    assert ctx.process.paths_read == ["fixtures/**"]
    assert ctx.process.paths_write == ["generated/**"]
    assert ctx.artifacts[0].values["amount"] == 1500
    assert ctx.commands[0].required == ["amount", "to"]
    assert ctx.commands[0].runtime == "executor:worker"
    assert ctx.resources[0].id == "mullm:rag"
    assert ctx.access[0].effect == "deny"
    assert ctx.runtimes[0].status == "available"


def test_doql_roundtrip_preserves_core_fields(tmp_path: Path) -> None:
    from nlp2dsl_sdk.doql import load_doql_context, render_doql_context, write_doql_context

    src = tmp_path / "environment.doql.less"
    src.write_text(
        """
environment[name="roundtrip"] {
  NLP2DSL_BACKEND_URL: "http://localhost:8010";
}
data { send_invoice.amount: 99; }
conversation { autofill: true; strict_pdf: true; }
commands[0] { name: "send_invoice"; required: "amount,to"; runtime: "executor:worker"; }
runtimes[0] { id: "executor:worker"; status: "available"; health: "http://localhost:8004/health"; }
""".strip()
        + "\n",
        encoding="utf-8",
    )

    original = load_doql_context(src)
    out = tmp_path / "out.doql.less"
    write_doql_context(out, original)
    loaded = load_doql_context(out)

    assert loaded.example_name == "roundtrip"
    assert loaded.data["send_invoice.amount"] == 99
    assert loaded.strict_pdf is True
    assert loaded.commands[0].name == "send_invoice"
    assert loaded.runtimes[0].health == "http://localhost:8004/health"
    assert "runtimes[0]" in render_doql_context(loaded)


def test_autofill_entities_from_data_and_aliases() -> None:
    ctx = DoqlTaskContext(
        data={
            "send_invoice.amount": 1500,
            "attachment_path": "fixtures/invoice.pdf",
        },
        autofill=True,
    )

    updated, filled = autofill_entities(
        {"intent": "send_invoice"},
        ["send_invoice.amount", "send_invoice.attachment"],
        ctx,
    )

    assert updated["amount"] == 1500
    assert updated["attachment_path"] == "fixtures/invoice.pdf"
    assert filled == ["send_invoice.amount", "send_invoice.attachment"]


def test_autofill_entities_from_artifact_values() -> None:
    ctx = DoqlTaskContext(
        data={"send_invoice.amount": 1500},
        artifacts=[
            DoqlArtifact(
                path="fixtures/invoice-request.txt",
                kind="metadata",
                values={"to": "client@example.com"},
            )
        ],
        autofill=True,
    )

    updated, filled = autofill_entities({}, ["send_invoice.to"], ctx)

    assert updated["to"] == "client@example.com"
    assert filled == ["send_invoice.to"]


def test_autofill_entities_disabled_returns_original_object() -> None:
    entities = {"intent": "send_invoice"}
    ctx = DoqlTaskContext(data={"send_invoice.amount": 1500}, autofill=False)

    updated, filled = autofill_entities(entities, ["send_invoice.amount"], ctx)

    assert updated is entities
    assert filled == []
