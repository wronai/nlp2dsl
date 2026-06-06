"""
SystemMapIR — runtime schema map for nlp2dsl structure generation.

Target: LLM introspects the environment and emits validated SystemMapIR
(Pydantic models, MIME types, Propact/workflow protocols) instead of
hardcoded collect_task_context() blocks.

See docs/doql-dynamic-generation.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MimeTypeSpec(BaseModel):
    """Artifact or payload MIME + optional Pydantic schema reference."""

    type: str = Field(description="e.g. application/pdf, text/plain, application/json")
    schema_ref: str | None = Field(
        default=None,
        description="Name of Pydantic model or DOQL entity, e.g. InvoiceDocument",
    )
    encoding: str | None = None


class RuntimeSpecIR(BaseModel):
    """
    Execution environment available to the example (where effects run).

    Distinct from ProtocolSpec.transport (network path between services).
    """

    id: str = Field(description="e.g. executor:worker, orchestrator:nlp-service")
    kind: Literal[
        "orchestrator",
        "gateway",
        "worker",
        "llm",
        "database",
        "cache",
        "mock",
        "external",
    ] = "worker"
    url: str | None = None
    uri: str | None = None
    health: str | None = None
    docker_profile: str | None = None
    model: str | None = None
    roles: list[str] = Field(default_factory=list)
    status: Literal["available", "unavailable", "unknown"] = "unknown"


class ProtocolSpec(BaseModel):
    """
    Transport / execution protocol for a command step.

    Maps to Propact fenced blocks (propact:shell, propact:rest) or
    workflow MVP (backend→worker).
    """

    name: str = Field(description="propact:rest | propact:shell | workflow/run | mcp")
    target_kind: str = Field(default="unknown")
    endpoint: str | None = None
    transport: str | None = None
    risk: Literal["low", "medium", "high", "destructive"] = "low"


class FieldSpec(BaseModel):
    """Single command parameter with optional MIME/schema."""

    name: str
    required: bool = True
    mime: MimeTypeSpec | None = None
    description: str = ""


class CommandSchemaIR(BaseModel):
    """CMD layer schema — one workflow action / service call."""

    name: str
    description: str = ""
    runtime: str | None = Field(
        default=None,
        description="Reference to runtimes[].id where this command executes",
    )
    protocol: ProtocolSpec = Field(default_factory=lambda: ProtocolSpec(name="workflow/run"))
    fields: list[FieldSpec] = Field(default_factory=list)
    input_model: str | None = Field(
        default=None,
        description="Pydantic model name for full step config (generated at runtime)",
    )
    output_model: str | None = None

    @property
    def required_names(self) -> list[str]:
        return [f.name for f in self.fields if f.required]

    @property
    def optional_names(self) -> list[str]:
        return [f.name for f in self.fields if not f.required]


class ResourceSpecIR(BaseModel):
    id: str
    title: str = ""
    connector: str = ""
    uri_patterns: list[str] = Field(default_factory=list)
    mime_types: list[MimeTypeSpec] = Field(default_factory=list)


class AccessGrantIR(BaseModel):
    agent: str
    resource_area: str = ""
    actions: list[str] = Field(default_factory=list)
    effect: Literal["allow", "deny", "approval"] = "allow"


class ArtifactSpecIR(BaseModel):
    path: str
    kind: str = "file"
    mime: MimeTypeSpec | None = None
    values: dict[str, Any] = Field(default_factory=dict)
    exists: bool | None = None


class ConversationPolicyIR(BaseModel):
    autofill: bool = True
    attachment_required: bool = False
    generate_invoice_if_missing: bool = True
    sync_auto_execute: bool = False
    strict_pdf: bool = False


class ProcessAccessScopeIR(BaseModel):
    """Process-level ACL scope (subset of platform grants)."""

    agent: str = ""
    allow_resource_areas: list[str] = Field(default_factory=list)
    deny_resource_areas: list[str] = Field(default_factory=list)


class ProcessPathsIR(BaseModel):
    """Filesystem paths available to the process agent."""

    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)


class ProcessPolicyIR(BaseModel):
    """
    Per-example process behaviour — workflow style, NLP/LLM, Intract, paths.

    Merged from examples/example-profiles.yaml → rendered as process {} in DOQL.
    """

    mode: Literal["deterministic", "balanced", "reactive"] = "balanced"
    nlp_parser: Literal["rules", "rules_first", "auto", "llm"] = "auto"
    nlp_confidence_min: float = 0.5
    nlp_enrich_missing: bool = False
    llm_reasoning: Literal["shallow", "deep"] = "shallow"
    llm_temperature: float | None = None
    autonomous_enabled: bool = True
    autonomous_max_rounds: int = 8
    ask_user: Literal["never", "when_exhausted", "always_confirm"] = "when_exhausted"
    intract_gate: bool = False
    intract_enforce_clarification: bool = False
    access: ProcessAccessScopeIR = Field(default_factory=ProcessAccessScopeIR)
    paths: ProcessPathsIR = Field(default_factory=ProcessPathsIR)


class ScheduleSpecIR(BaseModel):
    """Cron / trigger schedule bound to a workflow or NL task."""

    id: str
    cron: str = Field(description="Cron expression, e.g. 0 9 * * *")
    task: str = Field(description="Natural language or workflow name to run")
    workflow_action: str | None = None
    enabled: bool = True
    timezone: str = "UTC"


class GeneratedServiceIR(BaseModel):
    """Optional service stub emitted under .nlp2dsl/generated/services/."""

    name: str
    description: str = ""
    image: str | None = None
    build_context: str | None = None
    roles: list[str] = Field(default_factory=list)


class DeploySpecIR(BaseModel):
    """Docker Compose deployment descriptor for transparent process execution."""

    target: str = "docker-compose"
    platform_compose: str = "docker-compose.yml"
    mocks_compose: str = "examples/docker-compose.yml"
    stack_compose: str = ".nlp2dsl/generated/docker-compose.stack.yaml"
    docker_profiles: list[str] = Field(default_factory=list)
    cron_service: str = "invoice-stack-cron"
    cron_image: str = "mcuadros/ofelia:latest"


class ProfileValidationIR(BaseModel):
    """Example-profile acceptance check — maps example-profiles.yaml validations → runtime codes."""

    code: str = Field(description="Stable code, e.g. profile.dsl_action")
    action: str = ""
    status: str = ""
    path: str = ""


class SystemMapIR(BaseModel):
    """
    nlp2dsl.system_map.v1 — canonical map of available system capabilities.

    Generated at runtime by SystemMapGenerator (LLM + introspection),
    validated by Pydantic, rendered to environment.doql.less or consumed directly.
    """

    format: str = "nlp2dsl.system_map.v1"
    version: int = 1
    example_id: str = ""
    environment: dict[str, str] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    runtimes: list[RuntimeSpecIR] = Field(default_factory=list)
    commands: list[CommandSchemaIR] = Field(default_factory=list)
    resources: list[ResourceSpecIR] = Field(default_factory=list)
    access: list[AccessGrantIR] = Field(default_factory=list)
    artifacts: list[ArtifactSpecIR] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    workflow_history: dict[str, Any] = Field(default_factory=dict)
    conversation: ConversationPolicyIR = Field(default_factory=ConversationPolicyIR)
    process: ProcessPolicyIR = Field(default_factory=ProcessPolicyIR)
    schedules: list[ScheduleSpecIR] = Field(default_factory=list)
    deploy: DeploySpecIR | None = None
    generated_services: list[GeneratedServiceIR] = Field(default_factory=list)
    validations: list[ProfileValidationIR] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def command(self, name: str) -> CommandSchemaIR | None:
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None

    def runtime(self, runtime_id: str) -> RuntimeSpecIR | None:
        for rt in self.runtimes:
            if rt.id == runtime_id:
                return rt
        return None

    def runtime_for_command(self, action: str) -> RuntimeSpecIR | None:
        cmd = self.command(action)
        if cmd is None or not cmd.runtime:
            return None
        return self.runtime(cmd.runtime)

    def validate_step_config(self, action: str, config: dict[str, Any]) -> list[str]:
        """Return missing field names for action against this map."""
        schema = self.command(action)
        if schema is None:
            return [f"unknown_action:{action}"]
        missing: list[str] = []
        for field in schema.fields:
            if not field.required:
                continue
            val = config.get(field.name)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(field.name)
        return missing
