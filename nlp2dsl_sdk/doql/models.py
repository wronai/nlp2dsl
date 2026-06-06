"""DOQL dataclasses — extracted from doql_context (god module split)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..system_map_ir import ProfileValidationIR


@dataclass
class DoqlArtifact:
    path: str
    kind: str = "file"
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoqlRuntime:
    """Execution environment (where command effects run)."""

    id: str
    kind: str = "worker"
    url: str = ""
    uri: str = ""
    health: str = ""
    docker_profile: str = ""
    model: str = ""
    roles: list[str] = field(default_factory=list)
    status: str = "unknown"


@dataclass
class DoqlCommand:
    """Schema kroku CMD — akcja workflow + wymagane pola + runtime + transport."""

    name: str
    description: str = ""
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    runtime: str = ""
    transport: str = "backend→worker"
    endpoint: str = "POST /workflow/run"


@dataclass
class DoqlResource:
    id: str
    title: str = ""
    connector: str = ""
    uri_patterns: list[str] = field(default_factory=list)


@dataclass
class DoqlAccess:
    agent: str
    resource_area: str = ""
    actions: list[str] = field(default_factory=list)
    effect: str = "allow"


@dataclass
class DoqlProcessPolicy:
    mode: str = "balanced"
    nlp_parser: str = "auto"
    nlp_confidence_min: float = 0.5
    nlp_enrich_missing: bool = False
    llm_reasoning: str = "shallow"
    llm_temperature: float | None = None
    autonomous_enabled: bool = True
    autonomous_max_rounds: int = 8
    ask_user: str = "when_exhausted"
    intract_gate: bool = False
    intract_enforce_clarification: bool = False
    agent: str = ""
    allow_resource_areas: list[str] = field(default_factory=list)
    deny_resource_areas: list[str] = field(default_factory=list)
    paths_read: list[str] = field(default_factory=list)
    paths_write: list[str] = field(default_factory=list)


@dataclass
class DoqlTaskContext:
    example_name: str = ""
    generated_at: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[DoqlArtifact] = field(default_factory=list)
    commands: list[DoqlCommand] = field(default_factory=list)
    resources: list[DoqlResource] = field(default_factory=list)
    access: list[DoqlAccess] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    workflow_history: dict[str, Any] = field(default_factory=dict)
    autofill: bool = True
    sync_auto_execute: bool = False
    attachment_required: bool = False
    generate_invoice_if_missing: bool = True
    strict_pdf: bool = False
    runtimes: list[DoqlRuntime] = field(default_factory=list)
    process: DoqlProcessPolicy = field(default_factory=DoqlProcessPolicy)
    validations: list[ProfileValidationIR] = field(default_factory=list)

    def entity_values(self, action: str) -> dict[str, Any]:
        prefix = f"{action}."
        out: dict[str, Any] = {}
        for key, value in self.data.items():
            if key.startswith(prefix):
                out[key[len(prefix) :]] = value
            elif "." not in key and action == "send_invoice":
                out[key] = value
        return out

    def command(self, name: str) -> DoqlCommand | None:
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None

    def required_fields_for(self, action: str) -> list[str] | None:
        cmd = self.command(action)
        if cmd and cmd.required:
            return list(cmd.required)
        return None

    def runtime_for(self, action: str) -> str | None:
        cmd = self.command(action)
        if cmd and cmd.runtime:
            return cmd.runtime
        from ..validation.rules.runtime_health import runtime_id_for_intent

        rt = runtime_id_for_intent(action)
        if rt and any(r.id == rt for r in self.runtimes):
            return rt
        return rt
