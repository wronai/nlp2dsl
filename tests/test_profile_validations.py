"""Tests for example-profile validations (C3)."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.system_map_ir import ProfileValidationIR, SystemMapIR
from nlp2dsl_sdk.validation.profile_checks import (
    parse_profile_validation,
    parse_profile_validations,
    run_profile_validation_checks,
    validate_profile_expectations,
)
from nlp2dsl_sdk.validation.profile_checks import ProfileCheckContext
from nlp2dsl_sdk.system_map_render import render_system_map_doql
from nlp2dsl_sdk.process_policy import apply_process_policies


def test_parse_shorthand_validations() -> None:
    specs = parse_profile_validations(
        [
            {"execution_status": "completed"},
            {"dsl_action": "send_invoice"},
            {"conversation_status": "executed"},
            {"artifact_exists": ".nlp2dsl/generated/stack.yaml"},
        ]
    )
    assert [s.code for s in specs] == [
        "profile.execution_completed",
        "profile.dsl_action",
        "profile.conversation_executed",
        "profile.artifact_exists",
    ]
    assert specs[1].action == "send_invoice"
    assert specs[3].path == ".nlp2dsl/generated/stack.yaml"


def test_parse_scenario_typed_validation() -> None:
    spec = parse_profile_validation({"type": "dsl_action", "action": "send_email"})
    assert spec is not None
    assert spec.code == "profile.dsl_action"
    assert spec.action == "send_email"


def test_dsl_action_check_pass_and_fail() -> None:
    response = {
        "dsl": {"steps": [{"action": "send_invoice", "config": {}}]},
        "status": "ready",
    }
    spec = ProfileValidationIR(code="profile.dsl_action", action="send_invoice")
    ctx = ProfileCheckContext(response=response)
    results = run_profile_validation_checks([spec], ctx)
    assert results[0]["passed"] is True

    spec_bad = ProfileValidationIR(code="profile.dsl_action", action="send_email")
    results_bad = run_profile_validation_checks([spec_bad], ctx)
    assert results_bad[0]["passed"] is False
    assert "send_email" in results_bad[0]["summary"]


def test_execution_and_conversation_checks() -> None:
    executed = {
        "status": "executed",
        "execution": {"status": "completed", "steps": [{"status": "completed"}]},
        "dsl": {"steps": [{"action": "send_invoice"}]},
    }
    ctx = ProfileCheckContext(response=executed)
    specs = parse_profile_validations(
        [{"execution_status": "completed"}, {"conversation_status": "executed"}]
    )
    results = run_profile_validation_checks(specs, ctx)
    assert all(r["passed"] for r in results)


def test_artifact_exists_check(tmp_path: Path) -> None:
    artifact = tmp_path / "out" / "stack.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("services: []\n", encoding="utf-8")

    spec = ProfileValidationIR(code="profile.artifact_exists", path="out/stack.yaml")
    ctx = ProfileCheckContext(response={}, example_dir=tmp_path)
    results = run_profile_validation_checks([spec], ctx)
    assert results[0]["passed"] is True


def test_apply_profile_validations_to_ir() -> None:
    ir = SystemMapIR(example_id="01-invoice")
    apply_process_policies(ir, example_id="01-invoice", repo_root=Path(__file__).resolve().parents[1])
    assert any(v.code == "profile.dsl_action" and v.action == "send_invoice" for v in ir.validations)
    doql = render_system_map_doql(ir)
    assert "validations[" in doql
    assert 'code: "profile.dsl_action"' in doql


def test_validate_profile_expectations_issues() -> None:
    ir = SystemMapIR(
        example_id="test",
        validations=[ProfileValidationIR(code="profile.dsl_action", action="notify_slack")],
    )
    issues = validate_profile_expectations(
        ir,
        {"dsl": {"steps": [{"action": "send_invoice"}]}},
    )
    assert len(issues) == 1
    assert issues[0].code == "profile.dsl_action"
