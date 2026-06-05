"""Tests for compose_generator — stack + cron artifact emission."""

from __future__ import annotations

from pathlib import Path

import yaml

from nlp2dsl_sdk.compose_generator import generate_stack_compose
from nlp2dsl_sdk.system_map_ir import DeploySpecIR, ScheduleSpecIR, SystemMapIR


def test_generate_stack_compose_writes_artifacts(tmp_path: Path) -> None:
    ex = tmp_path / "13-autonomous-invoice-stack"
    ex.mkdir()
    (ex / "fixtures").mkdir()

    ir = SystemMapIR(
        example_id="13-autonomous-invoice-stack",
        schedules=[
            ScheduleSpecIR(
                id="daily-invoice",
                cron="0 9 * * *",
                task="Wyślij fakturę",
                workflow_action="send_invoice",
            )
        ],
        deploy=DeploySpecIR(
            docker_profiles=["invoice", "autonomous-stack"],
            stack_compose=".nlp2dsl/generated/docker-compose.stack.yaml",
        ),
    )

    result = generate_stack_compose(ir, example_dir=ex, example_id="13-autonomous-invoice-stack")

    assert result.stack_compose.is_file()
    assert result.ofelia_ini.is_file()
    assert result.run_script.is_file()
    assert result.manifest.is_file()
    assert result.generated_services

    payload = yaml.safe_load(result.stack_compose.read_text(encoding="utf-8"))
    assert "invoice-stack-cron" in payload["services"]
    assert "autonomous-stack" in payload["services"]["invoice-stack-cron"]["profiles"]

    ini = result.ofelia_ini.read_text(encoding="utf-8")
    assert "0 9 * * *" in ini
    assert "daily-invoice" in ini

    manifest = yaml.safe_load(result.manifest.read_text(encoding="utf-8"))
    assert manifest["example_id"] == "13-autonomous-invoice-stack"
    assert "up_command" in manifest


def test_enrich_ir_adds_defaults(tmp_path: Path) -> None:
    ex = tmp_path / "13-autonomous-invoice-stack"
    ex.mkdir()

    ir = SystemMapIR(example_id="13-autonomous-invoice-stack")
    result = generate_stack_compose(ir, example_dir=ex)

    reg_content = (ex / ".nlp2dsl/registry/environment.doql.less")
    # registry not auto-written by generator — schedules in manifest
    manifest = yaml.safe_load(result.manifest.read_text(encoding="utf-8"))
    assert len(manifest["schedules"]) >= 1
    assert manifest["deploy"]["target"] == "docker-compose"
