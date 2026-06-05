"""Tests for SystemMapIR and DOQL render."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nlp2dsl_sdk.doql_context import collect_task_context
from nlp2dsl_sdk.system_map_bridge import doql_file_to_system_map, task_context_to_system_map
from nlp2dsl_sdk.system_map_generator import generate_system_map
from nlp2dsl_sdk.system_map_ir import (
    CommandSchemaIR,
    FieldSpec,
    MimeTypeSpec,
    RuntimeSpecIR,
    SystemMapIR,
)
from nlp2dsl_sdk.system_map_models import command_input_model, validate_config_against_map
from nlp2dsl_sdk.system_map_render import render_system_map_doql
from nlp2dsl_sdk.system_map_runtimes import build_runtimes_for_example, resolve_command_runtime


def test_system_map_validate_step_config() -> None:
    ir = SystemMapIR(
        example_id="test",
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                fields=[
                    FieldSpec(name="amount", required=True),
                    FieldSpec(name="to", required=True),
                    FieldSpec(
                        name="attachment_path",
                        required=False,
                        mime=MimeTypeSpec(type="application/pdf", schema_ref="InvoiceDocument"),
                    ),
                ],
            )
        ],
    )
    missing = ir.validate_step_config("send_invoice", {"amount": 1500})
    assert missing == ["to"]
    assert ir.validate_step_config("send_invoice", {"amount": 1500, "to": "a@b.pl"}) == []


def test_dynamic_command_input_model() -> None:
    ir = SystemMapIR(
        example_id="test",
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                input_model="SendInvoiceConfig",
                fields=[
                    FieldSpec(name="amount", required=True),
                    FieldSpec(name="to", required=True),
                    FieldSpec(
                        name="attachment_path",
                        required=False,
                        mime=MimeTypeSpec(type="application/pdf"),
                    ),
                ],
            )
        ],
    )
    model = command_input_model(ir.commands[0])
    assert model.__name__ == "SendInvoiceConfig"
    validated = validate_config_against_map(
        ir, "send_invoice", {"amount": 1500, "to": "a@b.pl", "attachment_path": "/tmp/x.pdf"}
    )
    assert validated["amount"] == 1500
    with pytest.raises(ValidationError):
        validate_config_against_map(ir, "send_invoice", {"amount": 1500})


def test_task_context_to_system_map_and_render() -> None:
    ctx = collect_task_context("examples/01-invoice", example_name="01-invoice", environment={})
    ir = task_context_to_system_map(ctx, example_dir="examples/01-invoice")
    assert ir.format == "nlp2dsl.system_map.v1"
    assert any(c.name == "send_invoice" for c in ir.commands)
    send = ir.command("send_invoice")
    assert send is not None
    assert send.runtime == "executor:worker"
    assert send.required_names == ["amount", "to"]
    assert len(ir.runtimes) >= 5
    assert ir.runtime("executor:worker") is not None
    doql = render_system_map_doql(ir)
    assert "runtimes[" in doql
    assert 'runtime: "executor:worker"' in doql
    assert "commands[" in doql
    assert "nlp2dsl.system_map.v1" in doql


def test_build_runtimes_for_01_invoice() -> None:
    runtimes = build_runtimes_for_example(
        "01-invoice",
        example_dir="examples/01-invoice",
        environment={"NLP2DSL_BACKEND_URL": "http://localhost:8010"},
    )
    ids = {r.id for r in runtimes}
    assert "executor:worker" in ids
    assert "gateway:backend" in ids
    assert "orchestrator:nlp-service" in ids
    worker = next(r for r in runtimes if r.id == "executor:worker")
    assert worker.status == "available"
    assert "invoice" in (worker.docker_profile or "")


def test_resolve_command_runtime() -> None:
    assert resolve_command_runtime("send_invoice", profile={"services": ["worker"]}) == "executor:worker"
    assert resolve_command_runtime("system_file_list") == "orchestrator:nlp-service"
    assert resolve_command_runtime("mullm_shell_task") == "delegate:mullm"


def test_doql_roundtrip_runtimes(tmp_path) -> None:
    ir = SystemMapIR(
        example_id="roundtrip",
        runtimes=[
            RuntimeSpecIR(id="executor:worker", kind="worker", status="available"),
        ],
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                runtime="executor:worker",
                fields=[FieldSpec(name="amount", required=True), FieldSpec(name="to", required=True)],
            )
        ],
    )
    doql = render_system_map_doql(ir)
    path = tmp_path / "environment.doql.less"
    path.write_text(doql, encoding="utf-8")
    loaded = doql_file_to_system_map(path)
    assert loaded.runtimes[0].id == "executor:worker"
    assert loaded.commands[0].runtime == "executor:worker"


def test_generate_system_map_01_invoice() -> None:
    ir = generate_system_map("examples/01-invoice", example_id="01-invoice")
    assert any(c.name == "send_invoice" for c in ir.commands)
    assert ir.runtimes
