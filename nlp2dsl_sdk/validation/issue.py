"""Structured validation issues — stable codes for reflection and autonomous repair."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

IssueKind = Literal["missing", "mismatch", "invalid_format", "blocked", "unknown_action"]
Resolution = Literal["autofill", "generate", "ask_user", "fix_format", "blocked", "none"]


class Phase(str, Enum):
    PREFLIGHT = "preflight"
    DSL_READY = "dsl_ready"
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    POST_HEALTH = "post_health"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field_name: str = ""
    message: str = ""
    phase: Phase = Phase.DSL_READY
    kind: IssueKind = "invalid_format"
    resolution: Resolution = "ask_user"
    source_hint: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Stable JSON payload for API responses and autonomous repair traces."""
        return {
            "code": self.code,
            "field": self.field_name,
            "message": self.to_legacy_message(),
            "phase": self.phase.value,
            "kind": self.kind,
            "resolution": self.resolution,
            "source_hint": self.source_hint,
            "meta": dict(self.meta),
        }

    def to_legacy_message(self) -> str:
        """Polish string consumed by existing orchestrator / reflection fallbacks."""
        if self.message:
            return self.message
        if self.code == "field.missing":
            return f"brak wymaganego pola: {self.field_name}"
        if self.code == "field.quality_missing":
            return f"brak pola jakości: {self.field_name}"
        if self.code == "action.unknown":
            return f"unknown_action:{self.meta.get('action', self.field_name)}"
        if self.code == "attachment.missing":
            return "brak attachment_path (conversation.attachment_required)"
        return f"{self.field_name or self.code}: {self.message or self.code}"


def issues_to_messages(issues: list[ValidationIssue]) -> list[str]:
    return [i.to_legacy_message() for i in issues]
