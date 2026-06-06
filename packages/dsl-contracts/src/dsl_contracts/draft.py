"""LLM-generated contract drafts — draft → validate → approve → active."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from dsl_contracts.issue import ValidationIssue
from dsl_contracts.registry import contract_from_registry_entry

ContractDraftStatus = Literal["draft", "validated", "approved", "active", "rejected"]

DEFAULT_DRAFTS_DIR = Path(".nlp2dsl/generated/contracts")
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]", re.MULTILINE),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
)

FORBIDDEN_DRAFT_STATUSES_FOR_RUNTIME = frozenset({"draft", "validated", "rejected"})


class ContractDraft(BaseModel):
    """Proposed action contract awaiting human or CI approval."""

    name: str
    status: ContractDraftStatus = "draft"
    source: str = "llm"
    contract: dict[str, Any] = Field(default_factory=dict)
    validators: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None
    approved_by: str | None = None

    def to_yaml_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


def drafts_dir(root: Path | str | None = None) -> Path:
    base = Path(root) if root else Path.cwd()
    return base / DEFAULT_DRAFTS_DIR


def draft_path(name: str, *, root: Path | str | None = None) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_") or "unnamed"
    return drafts_dir(root) / f"{safe}.draft.yaml"


def load_draft(path: Path | str) -> ContractDraft:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"draft file must be a mapping: {path}")
    return ContractDraft.model_validate(raw)


def save_draft(draft: ContractDraft, path: Path | str | None = None, *, root: Path | str | None = None) -> Path:
    target = Path(path) if path else draft_path(draft.name, root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    draft.updated_at = datetime.now(UTC).isoformat()
    target.write_text(
        yaml.safe_dump(draft.to_yaml_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return target


def list_draft_files(*, root: Path | str | None = None) -> list[Path]:
    directory = drafts_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.draft.yaml"))


def load_drafts(*, root: Path | str | None = None) -> list[ContractDraft]:
    return [load_draft(path) for path in list_draft_files(root=root)]


def validate_draft(draft: ContractDraft) -> list[ValidationIssue]:
    """Static checks before a draft may move to approved/active."""
    issues: list[ValidationIssue] = []

    if not draft.name.strip():
        issues.append(
            ValidationIssue(
                code="contract.draft.missing_name",
                message="Draft contract requires non-empty name",
                kind="invalid_format",
                resolution="blocked",
            )
        )
        return issues

    if not draft.contract:
        issues.append(
            ValidationIssue(
                code="contract.draft.empty_contract",
                field_name="contract",
                message="Draft contract body is empty",
                kind="missing",
                resolution="blocked",
            )
        )
        return issues

    blob = yaml.safe_dump(draft.to_yaml_dict(), allow_unicode=True)
    for pattern in _SECRET_PATTERNS:
        if pattern.search(blob):
            issues.append(
                ValidationIssue(
                    code="contract.draft.secret_detected",
                    message="Draft appears to contain secrets — remove before approval",
                    kind="blocked",
                    resolution="blocked",
                )
            )
            break

    try:
        contract_from_registry_entry(draft.name, draft.contract)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="contract.draft.invalid_schema",
                message=f"Contract schema invalid: {exc}",
                kind="invalid_format",
                resolution="blocked",
            )
        )

    required = draft.contract.get("required") or []
    if not isinstance(required, list):
        issues.append(
            ValidationIssue(
                code="contract.draft.required_not_list",
                field_name="contract.required",
                message="required must be a list of field names",
                kind="invalid_format",
                resolution="blocked",
            )
        )

    return issues


def draft_ready_for_activation(draft: ContractDraft) -> bool:
    return draft.status in {"approved", "active"} and not validate_draft(draft)


def active_draft_contracts(*, root: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Return registry entries loadable at runtime from approved/active drafts only."""
    out: dict[str, dict[str, Any]] = {}
    for draft in load_drafts(root=root):
        if draft.status not in {"approved", "active"}:
            continue
        if validate_draft(draft):
            continue
        out[draft.name] = dict(draft.contract)
    return out
