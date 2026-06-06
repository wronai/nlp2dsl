"""Tests for nlp2dsl_sdk.validation pipeline."""

from __future__ import annotations

from nlp2dsl_sdk.invoice_pdf import write_invoice_pdf
from nlp2dsl_sdk.system_map_ir import CommandSchemaIR, FieldSpec, SystemMapIR
from nlp2dsl_sdk.validation import (
    Phase,
    legacy_message_to_issue,
    validate_dsl_contract_issues,
    validate_step_config_from_map,
    validate_step_config_from_map_issues,
)
from nlp2dsl_sdk.validation.issue import issues_to_messages


def test_legacy_message_to_issue_pdf() -> None:
    issue = legacy_message_to_issue("attachment_path: wymagany prawidłowy PDF (%PDF), a plik nim nie jest")
    assert issue.code == "attachment.invalid_pdf"
    assert issue.resolution == "generate"
    assert issue.field_name == "attachment_path"


def test_legacy_message_to_issue_missing_file() -> None:
    issue = legacy_message_to_issue("attachment_path: plik nie istnieje: /tmp/x.pdf")
    assert issue.code == "attachment.missing_file"
    assert issue.resolution == "generate"


def test_legacy_message_to_issue_variants() -> None:
    cases = [
        ("brak pola jakości: body", "field.quality_missing", "body", "ask_user"),
        ("to: nie wygląda na adres email: abc", "field.invalid_email", "to", "fix_format"),
        ("attachment_path: kwota w PDF 100 ≠ 150", "attachment.amount_mismatch", "attachment_path", "fix_format"),
        ("attachment_path: brak wymaganego %%EOF", "attachment.invalid_eof", "attachment_path", "ask_user"),
        ("unknown_action:new_plugin", "action.unknown", "action", "blocked"),
        ("brak action w kroku workflow", "workflow.missing_action", "action", "blocked"),
        ("nieznana walidacja", "validation.other", "", "ask_user"),
    ]

    for raw, code, field, resolution in cases:
        issue = legacy_message_to_issue(raw)
        assert (issue.code, issue.field_name, issue.resolution) == (code, field, resolution)


def test_validate_step_config_from_map_issues_structure(tmp_path) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "inv.pdf"
    write_invoice_pdf(pdf, to="a@b.pl", amount=1500, currency="PLN")

    import os

    os.environ["NLP2DSL_EXAMPLE_DIR"] = str(ex)

    ir = SystemMapIR(
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                fields=[FieldSpec(name="amount"), FieldSpec(name="to")],
            )
        ]
    )
    issues = validate_step_config_from_map_issues(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/inv.pdf"},
    )
    assert issues == []


def test_issues_to_messages_roundtrip() -> None:
    issue = legacy_message_to_issue("brak wymaganego pola: amount")
    msgs = issues_to_messages([issue])
    assert msgs == ["brak wymaganego pola: amount"]


def test_plan_resolutions_invalid_pdf() -> None:
    from nlp2dsl_sdk.validation import plan_resolutions
    from nlp2dsl_sdk.validation.issue import ValidationIssue

    issue = ValidationIssue(
        code="attachment.invalid_pdf",
        field_name="attachment_path",
        message="wymagany prawidłowy PDF",
        resolution="generate",
        source_hint="generate_invoice",
    )
    plans = plan_resolutions([issue])
    steps = [p.step for p in plans]
    assert steps == ["clear_field", "delete_generated_attachment", "pick_fixture", "generate"]


def test_plan_resolutions_deduplicates_attachment_repairs() -> None:
    from nlp2dsl_sdk.validation import plan_resolutions
    from nlp2dsl_sdk.validation.issue import ValidationIssue

    issues = [
        ValidationIssue(
            code="attachment.invalid_pdf",
            field_name="attachment_path",
            resolution="generate",
            source_hint="generate_invoice",
        ),
        ValidationIssue(
            code="attachment.invalid_eof",
            field_name="attachment_path",
            resolution="generate",
            source_hint="generate_invoice",
        ),
    ]

    plans = plan_resolutions(issues)
    assert [plan.step for plan in plans] == [
        "clear_field",
        "delete_generated_attachment",
        "pick_fixture",
        "generate",
    ]


def test_plan_resolutions_autofill_issue() -> None:
    from nlp2dsl_sdk.validation import plan_resolutions
    from nlp2dsl_sdk.validation.issue import ValidationIssue

    issue = ValidationIssue(
        code="field.autofill_available",
        field_name="to",
        resolution="autofill",
        source_hint="doql.data",
    )

    plans = plan_resolutions([issue])
    assert len(plans) == 1
    assert plans[0].step == "autofill"
    assert plans[0].field == "to"
    assert plans[0].source_hint == "doql.data"


def test_apply_resolution_plans_stops_after_fixture() -> None:
    from nlp2dsl_sdk.validation import ResolutionEnvironment, apply_resolution_plans, plan_resolutions
    from nlp2dsl_sdk.validation.issue import ValidationIssue

    issue = ValidationIssue(
        code="attachment.missing_file",
        field_name="attachment_path",
        resolution="generate",
        source_hint="generate_invoice",
    )
    cleared: list[str] = []

    env = ResolutionEnvironment(
        clear_field=lambda f: cleared.append(f),
        delete_generated_attachment=lambda _raw: None,
        get_attachment_path=lambda: "",
        pick_fixture=lambda: "attachment_path ← fixtures/inv.pdf",
        generate=lambda _hint: "should not run",
        autofill=lambda _issue: None,
    )
    applied = apply_resolution_plans(plan_resolutions([issue]), env)
    assert "attachment_path ← fixtures/inv.pdf" in applied
    assert cleared == ["attachment_path"]


def test_filter_plans_by_reflection_tokens() -> None:
    from nlp2dsl_sdk.validation import filter_plans_by_reflection_tokens, plan_resolutions
    from nlp2dsl_sdk.validation.issue import ValidationIssue

    issue = ValidationIssue(
        code="attachment.invalid_pdf",
        field_name="attachment_path",
        resolution="generate",
        source_hint="generate_invoice",
    )
    autofill = ValidationIssue(
        code="field.missing",
        field_name="to",
        resolution="autofill",
        source_hint="data.send_invoice.to",
    )
    plans = plan_resolutions([issue, autofill])

    generate_only = filter_plans_by_reflection_tokens(plans, ["generate:generate_invoice"])
    assert all(p.step != "autofill" for p in generate_only)
    assert any(p.step == "generate" for p in generate_only)

    autofill_only = filter_plans_by_reflection_tokens(plans, ["autofill:data.send_invoice.to"])
    assert all(p.step == "autofill" for p in autofill_only)


def test_runtime_health_unavailable() -> None:
    from nlp2dsl_sdk.doql.models import DoqlRuntime
    from nlp2dsl_sdk.validation.rules.runtime_health import validate_runtime_health_for_intent

    issues = validate_runtime_health_for_intent(
        [DoqlRuntime(id="executor:worker", status="unavailable")],
        "send_invoice",
        live_probe=False,
    )
    assert len(issues) == 1
    assert issues[0].code == "runtime.unavailable"


def test_runtime_id_for_intent() -> None:
    from nlp2dsl_sdk.validation.rules.runtime_health import runtime_id_for_intent

    assert runtime_id_for_intent("send_invoice") == "executor:worker"
    assert runtime_id_for_intent("mullm_shell_task") == "delegate:mullm"


def test_validate_step_config_from_map_backward_compat(tmp_path) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    bad = fixtures / "bad.pdf"
    bad.write_text("FAKTURA\n", encoding="utf-8")

    import os

    os.environ["NLP2DSL_EXAMPLE_DIR"] = str(ex)

    ir = SystemMapIR(
        commands=[
            CommandSchemaIR(
                name="send_invoice",
                fields=[FieldSpec(name="amount"), FieldSpec(name="to")],
            )
        ]
    )
    msgs = validate_step_config_from_map(
        ir,
        "send_invoice",
        {"amount": 1500, "to": "a@b.pl", "attachment_path": "fixtures/bad.pdf"},
        phase=Phase.DSL_READY,
    )
    assert any("%PDF" in m for m in msgs)


def test_validate_dsl_contract_rejects_broken_steps() -> None:
    issues = validate_dsl_contract_issues(
        {
            "name": "broken",
            "steps": [
                {"config": {"amount": 1500}},
                {"action": "send_email", "config": "not-a-dict"},
            ],
        }
    )

    assert [issue.code for issue in issues] == [
        "workflow.missing_action",
        "dsl.step.config_invalid",
    ]
    assert issues[0].field_name == "steps.0.action"
    assert issues[0].to_dict()["phase"] == "dsl_ready"


def test_validate_dsl_contract_allows_dynamic_actions_by_default() -> None:
    issues = validate_dsl_contract_issues(
        {
            "name": "plugin_workflow",
            "steps": [{"action": "llm_generated_plugin", "config": {"x": 1}}],
        }
    )

    assert issues == []


def test_validate_post_health_from_map() -> None:
    from nlp2dsl_sdk.system_map_ir import RuntimeSpecIR, SystemMapIR
    from nlp2dsl_sdk.validation.pipeline import validate_post_health_from_map

    ir = SystemMapIR(
        runtimes=[RuntimeSpecIR(id="executor:worker", status="unavailable")],
    )
    issues = validate_post_health_from_map(ir, "send_invoice", live_probe=False)
    assert len(issues) == 1
    assert issues[0].code == "runtime.unavailable"
    assert issues[0].phase.value == "post_health"


def test_validate_post_health_preflight_phase() -> None:
    from nlp2dsl_sdk.doql.models import DoqlRuntime
    from nlp2dsl_sdk.validation.pipeline import validate_post_health_for_intent
    from nlp2dsl_sdk.validation.issue import Phase

    issues = validate_post_health_for_intent(
        [DoqlRuntime(id="executor:worker", status="unavailable")],
        "send_invoice",
        live_probe=False,
        phase=Phase.PREFLIGHT,
    )
    assert issues[0].phase == Phase.PREFLIGHT


def test_validate_post_execute_execution_failed_step() -> None:
    from nlp2dsl_sdk.validation.pipeline import validate_post_execute_execution

    issues = validate_post_execute_execution(
        {"steps": [{"action": "send_invoice", "status": "failed", "error": "timeout"}]}
    )
    assert len(issues) == 1
    assert issues[0].code == "execution.step_failed"
    assert issues[0].phase.value == "post_execute"


def test_validate_post_execute_from_map_skips_required_fields() -> None:
    from nlp2dsl_sdk.system_map_ir import CommandSchemaIR, FieldSpec, SystemMapIR
    from nlp2dsl_sdk.validation.pipeline import validate_post_execute_from_map

    ir = SystemMapIR(
        commands=[
            CommandSchemaIR(
                name="send_email",
                fields=[FieldSpec(name="to"), FieldSpec(name="body")],
            )
        ]
    )
    issues = validate_post_execute_from_map(
        ir,
        "send_email",
        {"to": "a@b.pl"},
    )
    assert not any(i.code == "field.missing" for i in issues)
