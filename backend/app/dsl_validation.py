"""Backend adapter for executable DSL contract validation."""

from __future__ import annotations

from typing import Any

from nlp2dsl_sdk.validation.issue import Phase, ValidationIssue
from nlp2dsl_sdk.validation.rules.dsl_contract import validate_dsl_contract


def validate_dsl_for_execution(dsl: Any) -> list[ValidationIssue]:
    return validate_dsl_contract(dsl, phase=Phase.DSL_READY)


def validation_issue_payloads(issues: list[ValidationIssue]) -> list[dict[str, Any]]:
    return [issue.to_dict() for issue in issues]


def missing_fields_from_issues(issues: list[ValidationIssue]) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        if issue.kind != "missing" or not issue.field_name or issue.field_name in seen:
            continue
        seen.add(issue.field_name)
        fields.append(issue.field_name)
    return fields


def format_dsl_validation_message(issues: list[ValidationIssue]) -> str:
    lines = ["Walidacja DSL nie powiodła się:"]
    for issue in issues:
        lines.append(f"  • {issue.to_legacy_message()}")
    lines.append("Workflow nie został wykonany.")
    return "\n".join(lines)


def dsl_validation_response(dsl: Any, issues: list[ValidationIssue]) -> dict[str, Any]:
    missing = missing_fields_from_issues(issues)
    return {
        "status": "validation_failed",
        "dsl": dsl,
        "message": format_dsl_validation_message(issues),
        "validation_issues": validation_issue_payloads(issues),
        "missing_fields": missing,
        "missing": missing,
    }
