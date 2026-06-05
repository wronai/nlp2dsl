"""Bridge: static DoqlTaskContext (today) ↔ SystemMapIR (target)."""

from __future__ import annotations

from pathlib import Path

from .doql_context import DoqlArtifact, DoqlCommand, DoqlTaskContext, load_doql_context
from .system_map_ir import (
    AccessGrantIR,
    ArtifactSpecIR,
    CommandSchemaIR,
    ConversationPolicyIR,
    FieldSpec,
    MimeTypeSpec,
    ProtocolSpec,
    ResourceSpecIR,
    RuntimeSpecIR,
    SystemMapIR,
)
from .system_map_runtimes import build_runtimes_for_example, load_example_profile, resolve_command_runtime

# Bootstrap field schemas when services.yaml omits required/optional
_COMMAND_FIELDS: dict[str, tuple[list[str], list[str]]] = {
    "send_invoice": (["amount", "to"], ["currency", "attachment_path"]),
    "generate_invoice": (["amount", "to"], ["currency", "output_path"]),
    "send_email": (["to"], ["subject", "body"]),
    "generate_report": (["report_type"], ["format"]),
    "crm_update": (["record_id"], ["fields"]),
}


def _mime_for_artifact(art: DoqlArtifact) -> MimeTypeSpec | None:
    path = art.path.lower()
    if path.endswith(".pdf"):
        return MimeTypeSpec(type="application/pdf", schema_ref="InvoiceDocument")
    if path.endswith(".json"):
        return MimeTypeSpec(type="application/json")
    if path.endswith(".txt"):
        return MimeTypeSpec(type="text/plain", schema_ref="InvoiceMetadata")
    return None


def task_context_to_system_map(ctx: DoqlTaskContext, *, example_dir: Path | str | None = None) -> SystemMapIR:
    """Convert hardcoded/bootstrap context into SystemMapIR (migration helper)."""
    profile = None
    if example_dir is not None:
        root = Path(example_dir).resolve()
        repo_root = root.parent.parent if root.parent.name == "examples" else root.parent
        profile = load_example_profile(ctx.example_name, repo_root)

    commands: list[CommandSchemaIR] = []
    for cmd in ctx.commands or []:
        commands.append(_command_to_ir(cmd, profile=profile))
    if not commands and ctx.capabilities:
        for name in ctx.capabilities:
            commands.append(
                CommandSchemaIR(
                    name=name,
                    runtime=resolve_command_runtime(name, profile=profile),
                    protocol=ProtocolSpec(name="workflow/run", transport="backend→worker"),
                )
            )

    runtimes: list[RuntimeSpecIR] = []
    if ctx.runtimes:
        runtimes = [
            RuntimeSpecIR(
                id=r.id,
                kind=r.kind if r.kind in (
                    "orchestrator", "gateway", "worker", "llm", "database", "cache", "mock", "external"
                ) else "worker",
                url=r.url or None,
                uri=r.uri or None,
                health=r.health or None,
                docker_profile=r.docker_profile or None,
                model=r.model or None,
                roles=list(r.roles),
                status=r.status if r.status in ("available", "unavailable", "unknown") else "unknown",
            )
            for r in ctx.runtimes
        ]
    elif example_dir is not None:
        runtimes = build_runtimes_for_example(
            ctx.example_name,
            example_dir=example_dir,
            environment=ctx.environment,
        )

    return SystemMapIR(
        example_id=ctx.example_name,
        environment=dict(ctx.environment),
        data=dict(ctx.data),
        runtimes=runtimes,
        commands=commands,
        resources=[
            ResourceSpecIR(
                id=r.id,
                title=r.title,
                connector=r.connector,
                uri_patterns=list(r.uri_patterns),
            )
            for r in ctx.resources
        ],
        access=[
            AccessGrantIR(
                agent=a.agent,
                resource_area=a.resource_area,
                actions=list(a.actions),
                effect=a.effect if a.effect in ("allow", "deny", "approval") else "allow",
            )
            for a in ctx.access
        ],
        artifacts=[
            ArtifactSpecIR(
                path=a.path,
                kind=a.kind,
                mime=_mime_for_artifact(a),
                values=dict(a.values),
            )
            for a in ctx.artifacts
        ],
        capabilities=list(ctx.capabilities),
        workflow_history=dict(ctx.workflow_history),
        conversation=ConversationPolicyIR(
            autofill=ctx.autofill,
            attachment_required=ctx.attachment_required,
            generate_invoice_if_missing=ctx.generate_invoice_if_missing,
            sync_auto_execute=ctx.sync_auto_execute,
        ),
        metadata={"source": "doql_context.bootstrap"},
    )


def _command_to_ir(cmd: DoqlCommand, *, profile: dict | None = None) -> CommandSchemaIR:
    required = list(cmd.required)
    optional = list(cmd.optional)
    if not required and cmd.name in _COMMAND_FIELDS:
        required, optional = _COMMAND_FIELDS[cmd.name]
    fields = [
        *[FieldSpec(name=n, required=True) for n in required],
        *[FieldSpec(name=n, required=False) for n in optional],
    ]
    protocol_name = "workflow/run"
    transport = cmd.transport
    if cmd.transport == "nlp-service/system":
        protocol_name = "propact:shell"
    elif "notify" in cmd.name:
        protocol_name = "workflow/run"
    runtime_id = cmd.runtime or resolve_command_runtime(cmd.name, profile=profile)
    if runtime_id == "orchestrator:nlp-service":
        transport = "nlp-service/system"
    elif runtime_id == "delegate:mullm":
        transport = "nlp-service→mullm"
    elif runtime_id == "executor:worker":
        transport = "gateway:backend→executor:worker"
    return CommandSchemaIR(
        name=cmd.name,
        description=cmd.description,
        runtime=runtime_id,
        protocol=ProtocolSpec(
            name=protocol_name,
            transport=transport,
            endpoint=cmd.endpoint,
        ),
        fields=fields,
        input_model=f"{''.join(p.title() for p in cmd.name.split('_'))}Config",
    )


def doql_file_to_system_map(path: Path | str) -> SystemMapIR:
    """Parse environment.doql.less → SystemMapIR (round-trip via DoqlTaskContext)."""
    path = Path(path)
    ctx = load_doql_context(path)
    return task_context_to_system_map(ctx, example_dir=path.parent.parent)
