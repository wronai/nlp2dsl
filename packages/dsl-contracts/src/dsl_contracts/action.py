"""Canonical action contract models.

The first migration step wraps the existing registry dictionaries without
changing their public API. New runtime layers should depend on these models
instead of ad hoc registry dicts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CompatibilityMode = Literal["backward", "forward", "breaking", "unknown"]
ExecutionBackend = Literal["worker", "system", "delegate", "mullm", "unknown"]
IdempotencyMode = Literal["none", "optional", "required"]


class FieldContract(BaseModel):
    """Single input field expected by an action."""

    name: str
    type: str = "str"
    required: bool = True
    default: Any = None
    description: str = ""


class ExecutionContract(BaseModel):
    """How an action is executed once the DSL has been validated."""

    backend: ExecutionBackend = "worker"
    mode: str = "direct"
    side_effect: bool = True
    idempotency: IdempotencyMode = "optional"
    approval_required: bool = False


class CompatibilityContract(BaseModel):
    """Version matrix for contract, executor and event consumers."""

    contract_version: int = 1
    executor_version: str = "1"
    event_version: int = 1
    compatibility: CompatibilityMode = "backward"
    migrations: list[str] = Field(default_factory=list)


class ActionContract(BaseModel):
    """Source-of-truth description of an action."""

    name: str
    version: int = 1
    description: str = ""
    category: str = "business"
    required: list[str] = Field(default_factory=list)
    optional: dict[str, Any] = Field(default_factory=dict)
    quality_required: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    param_aliases: dict[str, str] = Field(default_factory=dict)
    input_model: str | None = None
    resource_area: str | None = None
    permission_action: str = "execute"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    execution: ExecutionContract = Field(default_factory=ExecutionContract)
    compatibility: CompatibilityContract = Field(default_factory=CompatibilityContract)

    @property
    def optional_fields(self) -> list[str]:
        return list(self.optional.keys())

    @property
    def all_fields(self) -> list[str]:
        names: list[str] = []
        for field in [*self.required, *self.optional_fields]:
            if field not in names:
                names.append(field)
        return names

    def to_catalog_entry(self) -> dict[str, Any]:
        """Backward-compatible `/nlp/actions` entry plus contract metadata."""
        return {
            "description": self.description or self.name,
            "required": list(self.required),
            "optional": self.optional_fields,
            "quality_required": list(self.quality_required),
            "aliases": list(self.aliases),
            "category": self.category,
            "contract_version": self.version,
            "execution_backend": self.execution.backend,
            "execution_mode": self.execution.mode,
            "idempotency": self.execution.idempotency,
            "approval_required": self.execution.approval_required,
            "input_model": self.input_model,
            "event_version": self.compatibility.event_version,
            "compatibility": self.compatibility.compatibility,
        }
