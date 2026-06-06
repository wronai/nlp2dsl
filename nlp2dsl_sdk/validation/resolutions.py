"""Map ValidationIssue → ordered repair plans (no side effects until apply)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from .issue import ValidationIssue

ResolutionStep = Literal[
    "clear_field",
    "delete_generated_attachment",
    "pick_fixture",
    "generate",
    "autofill",
]

_ATTACHMENT_CODES = frozenset(
    {
        "attachment.missing",
        "attachment.missing_file",
        "attachment.invalid_pdf",
        "attachment.invalid_eof",
        "attachment.amount_mismatch",
        "attachment.read_error",
        "attachment.path_denied",
    }
)

_INVALID_ATTACHMENT_CODES = frozenset(
    {
        "attachment.invalid_pdf",
        "attachment.invalid_eof",
        "attachment.amount_mismatch",
        "attachment.read_error",
    }
)


@dataclass(frozen=True)
class ResolutionPlan:
    step: ResolutionStep
    issue: ValidationIssue
    field: str = ""
    source_hint: str = ""


@dataclass
class ResolutionEnvironment:
    """Side-effect handlers injected by orchestrator / SDK flow."""

    clear_field: Callable[[str], None]
    delete_generated_attachment: Callable[[str], None]
    get_attachment_path: Callable[[], str]
    pick_fixture: Callable[[], str | None]
    generate: Callable[[str], str | None]
    autofill: Callable[[ValidationIssue], str | None]


def plan_resolutions(issues: list[ValidationIssue]) -> list[ResolutionPlan]:
    """Turn validation issues into an ordered, deduplicated repair sequence."""
    if not issues:
        return []

    plans: list[ResolutionPlan] = []
    seen: set[tuple[str, str, str]] = set()
    _append_attachment_plans(plans, seen, _attachment_issues(issues))
    _append_autofill_plans(plans, seen, issues)
    return plans


def _attachment_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [issue for issue in issues if _is_attachment_issue(issue)]


def _is_attachment_issue(issue: ValidationIssue) -> bool:
    return (
        issue.field_name == "attachment_path"
        or issue.code in _ATTACHMENT_CODES
        or issue.code.startswith("attachment.")
    )


def _append_attachment_plans(
    plans: list[ResolutionPlan],
    seen: set[tuple[str, str, str]],
    attachment: list[ValidationIssue],
) -> None:
    if not attachment:
        return

    primary = attachment[0]
    _append_plan(plans, seen, ResolutionPlan(step="clear_field", issue=primary, field="attachment_path"))

    if _has_invalid_attachment(attachment):
        _append_plan(
            plans,
            seen,
            ResolutionPlan(step="delete_generated_attachment", issue=primary, field="attachment_path"),
        )

    if _should_generate_attachment(attachment):
        _append_plan(plans, seen, ResolutionPlan(step="pick_fixture", issue=primary, field="attachment_path"))
        _append_plan(
            plans,
            seen,
            ResolutionPlan(
                step="generate",
                issue=primary,
                field="attachment_path",
                source_hint=_attachment_source_hint(attachment),
            ),
        )


def _append_autofill_plans(
    plans: list[ResolutionPlan],
    seen: set[tuple[str, str, str]],
    issues: list[ValidationIssue],
) -> None:
    for issue in issues:
        if not _is_autofill_issue(issue):
            continue
        _append_plan(
            plans,
            seen,
            ResolutionPlan(
                step="autofill",
                issue=issue,
                field=issue.field_name,
                source_hint=issue.source_hint or "",
            ),
        )


def _has_invalid_attachment(issues: list[ValidationIssue]) -> bool:
    return any(issue.code in _INVALID_ATTACHMENT_CODES for issue in issues)


def _should_generate_attachment(issues: list[ValidationIssue]) -> bool:
    return any(issue.resolution == "generate" for issue in issues)


def _attachment_source_hint(issues: list[ValidationIssue]) -> str:
    return next((issue.source_hint for issue in issues if issue.source_hint), "generate_invoice") or "generate_invoice"


def _is_autofill_issue(issue: ValidationIssue) -> bool:
    return issue.resolution == "autofill" and bool(issue.source_hint)


def filter_plans_by_reflection_tokens(
    plans: list[ResolutionPlan],
    tokens: list[str],
) -> list[ResolutionPlan]:
    """Keep repair plans allowed by reflection ``resolutions_available`` tokens (L4)."""
    if not tokens:
        return plans

    want_generate = any(token.startswith("generate:") for token in tokens)
    want_autofill = any(token.startswith("autofill:") for token in tokens)
    if not want_generate and not want_autofill:
        return plans

    attachment_steps = frozenset({"clear_field", "delete_generated_attachment", "pick_fixture", "generate"})
    filtered: list[ResolutionPlan] = []
    for plan in plans:
        if plan.step == "autofill":
            if want_autofill:
                filtered.append(plan)
        elif plan.step in attachment_steps:
            if want_generate:
                filtered.append(plan)
    return filtered if filtered else plans


def apply_resolution_plans(
    plans: list[ResolutionPlan],
    env: ResolutionEnvironment,
) -> list[str]:
    """Execute repair plans; stop after successful attachment acquisition."""
    applied: list[str] = []
    for plan in plans:
        if plan.step == "clear_field":
            env.clear_field(plan.field)
            applied.append(f"clear:{plan.field}")
        elif plan.step == "delete_generated_attachment":
            raw = env.get_attachment_path()
            if raw:
                env.delete_generated_attachment(raw)
                applied.append(f"deleted generated {plan.field}")
        elif plan.step == "pick_fixture":
            desc = env.pick_fixture()
            if desc:
                applied.append(desc)
                return applied
        elif plan.step == "generate":
            desc = env.generate(plan.source_hint or "generate_invoice")
            if desc:
                applied.append(desc)
                return applied
        elif plan.step == "autofill":
            desc = env.autofill(plan.issue)
            if desc:
                applied.append(desc)
    return applied


def _append_plan(
    plans: list[ResolutionPlan],
    seen: set[tuple[str, str, str]],
    plan: ResolutionPlan,
) -> None:
    key = (plan.step, plan.field, plan.source_hint)
    if key in seen:
        return
    seen.add(key)
    plans.append(plan)
