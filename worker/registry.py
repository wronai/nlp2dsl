"""Worker action registry validation vs nlp-service catalog (C1)."""

from __future__ import annotations

from typing import Iterable

from action_catalog import known_action_names_from_catalog, load_action_field_catalog

_CATALOG_TIMEOUT_SECONDS = float(__import__("os").getenv("WORKER_CATALOG_TIMEOUT", "5"))


def worker_eligible_catalog_actions(catalog: Iterable[str]) -> set[str]:
    """Business/worker actions from nlp-service — exclude system and Mullm delegates."""
    return {
        name
        for name in catalog
        if name
        and not name.startswith("system_")
        and not name.startswith("mullm_")
    }


def validate_handlers_against_catalog(
    handlers: Iterable[str],
    catalog: Iterable[str],
) -> list[str]:
    """Return human-readable drift warnings (empty list = OK)."""
    handler_set = set(handlers)
    catalog_set = set(catalog)
    eligible = worker_eligible_catalog_actions(catalog_set)
    issues: list[str] = []

    for name in sorted(handler_set - catalog_set):
        issues.append(f"Worker handler '{name}' is not listed in nlp-service catalog")

    for name in sorted(eligible - handler_set):
        issues.append(f"nlp-service catalog action '{name}' has no worker handler")

    return issues


def fetch_nlp_action_names(
    *,
    base_url: str | None = None,
    timeout: float = _CATALOG_TIMEOUT_SECONDS,
) -> set[str]:
    """Sync fetch of action names from nlp-service (startup validation)."""
    catalog = load_action_field_catalog(
        nlp_service_url=base_url,
        force=True,
        timeout=timeout,
    )
    return known_action_names_from_catalog(catalog=catalog)
