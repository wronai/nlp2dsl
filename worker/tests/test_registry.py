"""Tests for worker registry validation (C1)."""

from __future__ import annotations

from registry import validate_handlers_against_catalog, worker_eligible_catalog_actions


def test_worker_eligible_catalog_excludes_system_and_mullm() -> None:
    catalog = {"send_invoice", "system_status", "mullm_shell_task", "send_email"}
    assert worker_eligible_catalog_actions(catalog) == {"send_invoice", "send_email"}


def test_validate_handlers_reports_missing_handler() -> None:
    catalog = {"send_invoice", "send_email", "generate_report", "system_status"}
    handlers = {"send_invoice", "send_email"}
    issues = validate_handlers_against_catalog(handlers, catalog)
    assert any("generate_report" in issue for issue in issues)
    assert not any("system_status" in issue for issue in issues)


def test_validate_handlers_reports_unknown_handler() -> None:
    catalog = {"send_invoice", "send_email"}
    handlers = {"send_invoice", "legacy_action"}
    issues = validate_handlers_against_catalog(handlers, catalog)
    assert any("legacy_action" in issue for issue in issues)
