"""Validation context — everything needed to validate one step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .issue import Phase


PathScopeFn = Callable[[str], str | None]
PathResolverFn = Callable[[str], str]


@dataclass
class ValidationContext:
    phase: Phase
    action: str
    config: dict[str, Any]
    required_fields: list[str] = field(default_factory=list)
    quality_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    attachment_required: bool = False
    known_actions: set[str] | None = None
    path_resolver: PathResolverFn | None = None
    path_scope_check: PathScopeFn | None = None
    runtimes: list[Any] | None = None
    runtime_id: str | None = None

    @classmethod
    def from_map(
        cls,
        *,
        phase: Phase,
        action: str,
        config: dict[str, Any] | None,
        required: list[str],
        quality: list[str] | None = None,
        attachment_required: bool = False,
    ) -> ValidationContext:
        return cls(
            phase=phase,
            action=action,
            config=dict(config or {}),
            required_fields=list(required),
            quality_fields=list(quality or []),
            attachment_required=attachment_required,
        )
