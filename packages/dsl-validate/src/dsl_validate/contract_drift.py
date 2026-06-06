"""Action catalog drift detection across nlp-service, worker and backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dsl_contracts.registry import (
    quality_fields_for_action,
    required_fields_for_action,
)


@dataclass(frozen=True)
class CatalogDriftIssue:
    code: str
    message: str
    action: str | None = None
    source: str = "catalog"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "action": self.action,
            "source": self.source,
        }


@dataclass
class CatalogDriftReport:
    ok: bool = True
    issues: list[CatalogDriftIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issue_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def worker_eligible_actions(catalog: Iterable[str]) -> set[str]:
    """Business/worker actions — exclude system and Mullm delegates."""
    return {
        name
        for name in catalog
        if name and not name.startswith("system_") and not name.startswith("mullm_")
    }


def validate_handler_drift(
    handler_names: Iterable[str],
    catalog_names: Iterable[str],
) -> list[CatalogDriftIssue]:
    """Compare worker handler registry vs nlp-service action names."""
    handlers = set(handler_names)
    catalog = set(catalog_names)
    eligible = worker_eligible_actions(catalog)
    issues: list[CatalogDriftIssue] = []

    for name in sorted(handlers - catalog):
        issues.append(
            CatalogDriftIssue(
                code="handler.unknown_in_catalog",
                action=name,
                message=f"Worker handler '{name}' is not listed in nlp-service catalog",
                source="worker",
            )
        )

    for name in sorted(eligible - handlers):
        issues.append(
            CatalogDriftIssue(
                code="handler.missing_for_catalog",
                action=name,
                message=f"nlp-service catalog action '{name}' has no worker handler",
                source="worker",
            )
        )

    return issues


def _field_sets(catalog: Mapping[str, Any], action: str) -> tuple[set[str], set[str]]:
    required = set(required_fields_for_action(action, catalog=catalog))
    quality = set(quality_fields_for_action(action, catalog=catalog))
    return required, quality


def validate_catalog_field_drift(
    primary: Mapping[str, Any],
    secondary: Mapping[str, Any],
    *,
    primary_label: str = "nlp-service",
    secondary_label: str = "backend",
    actions: Iterable[str] | None = None,
) -> list[CatalogDriftIssue]:
    """Compare required/quality fields between two /nlp/actions-shaped catalogs."""
    names = set(actions) if actions is not None else set(primary) | set(secondary)
    issues: list[CatalogDriftIssue] = []

    for action in sorted(names):
        req_a, qual_a = _field_sets(primary, action)
        req_b, qual_b = _field_sets(secondary, action)

        if req_a != req_b:
            issues.append(
                CatalogDriftIssue(
                    code="catalog.required_drift",
                    action=action,
                    message=(
                        f"Required fields drift for '{action}': "
                        f"{primary_label}={sorted(req_a)} vs {secondary_label}={sorted(req_b)}"
                    ),
                    source=secondary_label,
                )
            )

        if qual_a != qual_b:
            issues.append(
                CatalogDriftIssue(
                    code="catalog.quality_drift",
                    action=action,
                    message=(
                        f"Quality fields drift for '{action}': "
                        f"{primary_label}={sorted(qual_a)} vs {secondary_label}={sorted(qual_b)}"
                    ),
                    source=secondary_label,
                )
            )

    return issues


def build_catalog_drift_report(
    *,
    nlp_catalog: Mapping[str, Any],
    worker_handlers: Iterable[str],
    backend_catalog: Mapping[str, Any] | None = None,
) -> CatalogDriftReport:
    """Full drift report for CI and preflight gates."""
    issues: list[CatalogDriftIssue] = []
    nlp_names = sorted(nlp_catalog)

    issues.extend(validate_handler_drift(worker_handlers, nlp_names))

    if backend_catalog is not None:
        shared = worker_eligible_actions(nlp_names) & worker_eligible_actions(backend_catalog)
        issues.extend(
            validate_catalog_field_drift(
                nlp_catalog,
                backend_catalog,
                primary_label="nlp-service",
                secondary_label="backend",
                actions=shared,
            )
        )

    return CatalogDriftReport(ok=not issues, issues=issues)
