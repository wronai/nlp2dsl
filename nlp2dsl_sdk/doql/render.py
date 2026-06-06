"""DOQL render — write DoqlTaskContext to environment.doql.less."""

from __future__ import annotations

from pathlib import Path

from .models import DoqlTaskContext


def render_doql_context(ctx: DoqlTaskContext) -> str:
    lines = [
        f"// DOQL system map — {ctx.example_name}",
        "// role: schema of available services, commands, resources, artifacts, access",
        f"// generated: {ctx.generated_at}",
        "",
        f'environment[name="{ctx.example_name}"] {{',
    ]
    for key in sorted(ctx.environment):
        if key == "generated_at":
            continue
        safe = str(ctx.environment[key]).replace('"', '\\"')
        lines.append(f'  {key}: "{safe}";')
    lines.append("}")
    lines.append("")

    lines.append("data {")
    for key in sorted(ctx.data):
        val = ctx.data[key]
        if isinstance(val, str):
            safe = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'  {key}: "{safe}";')
        elif isinstance(val, bool):
            lines.append(f"  {key}: {'true' if val else 'false'};")
        else:
            lines.append(f"  {key}: {val};")
    lines.append("}")
    lines.append("")

    for idx, art in enumerate(ctx.artifacts):
        lines.append(f"artifacts[{idx}] {{")
        lines.append(f'  path: "{art.path}";')
        lines.append(f'  kind: "{art.kind}";')
        for k, v in sorted(art.values.items()):
            if isinstance(v, str):
                lines.append(f'  {k}: "{v}";')
            else:
                lines.append(f"  {k}: {v};")
        lines.append("}")
        lines.append("")

    for idx, cmd in enumerate(ctx.commands):
        lines.append(f"commands[{idx}] {{")
        lines.append(f'  name: "{cmd.name}";')
        if cmd.description:
            safe = cmd.description.replace('"', '\\"')
            lines.append(f'  description: "{safe}";')
        if cmd.required:
            lines.append(f'  required: "{",".join(cmd.required)}";')
        if cmd.optional:
            lines.append(f'  optional: "{",".join(cmd.optional)}";')
        if cmd.runtime:
            lines.append(f'  runtime: "{cmd.runtime}";')
        lines.append(f'  transport: "{cmd.transport}";')
        lines.append(f'  endpoint: "{cmd.endpoint}";')
        lines.append("}")
        lines.append("")

    for idx, res in enumerate(ctx.resources):
        lines.append(f"resources[{idx}] {{")
        lines.append(f'  id: "{res.id}";')
        if res.title:
            safe = res.title.replace('"', '\\"')
            lines.append(f'  title: "{safe}";')
        if res.connector:
            lines.append(f'  connector: "{res.connector}";')
        if res.uri_patterns:
            lines.append(f'  uri_patterns: "{",".join(res.uri_patterns)}";')
        lines.append("}")
        lines.append("")

    for idx, grant in enumerate(ctx.access):
        lines.append(f"access[{idx}] {{")
        lines.append(f'  agent: "{grant.agent}";')
        if grant.resource_area:
            lines.append(f'  resource_area: "{grant.resource_area}";')
        if grant.actions:
            lines.append(f'  actions: "{",".join(grant.actions)}";')
        lines.append(f'  effect: "{grant.effect}";')
        lines.append("}")
        lines.append("")

    for idx, rt in enumerate(ctx.runtimes):
        lines.append(f"runtimes[{idx}] {{")
        lines.append(f'  id: "{rt.id}";')
        if rt.kind:
            lines.append(f'  kind: "{rt.kind}";')
        if rt.url:
            lines.append(f'  url: "{rt.url}";')
        if rt.uri:
            lines.append(f'  uri: "{rt.uri}";')
        if rt.health:
            lines.append(f'  health: "{rt.health}";')
        if rt.docker_profile:
            lines.append(f'  docker_profile: "{rt.docker_profile}";')
        if rt.model:
            lines.append(f'  model: "{rt.model}";')
        if rt.roles:
            lines.append(f'  roles: "{",".join(rt.roles)}";')
        if rt.status:
            lines.append(f'  status: "{rt.status}";')
        lines.append("}")
        lines.append("")

    if ctx.capabilities:
        lines.append("capabilities {")
        lines.append(f'  actions: "{",".join(ctx.capabilities)}";')
        lines.append("}")

    if ctx.workflow_history:
        lines.append("")
        lines.append("workflow_history {")
        for key in sorted(ctx.workflow_history):
            val = ctx.workflow_history[key]
            if isinstance(val, list):
                lines.append(f'  {key}: "{",".join(str(v) for v in val)}";')
            elif isinstance(val, str):
                lines.append(f'  {key}: "{val}";')
            else:
                lines.append(f"  {key}: {val};")
        lines.append("}")

    proc = ctx.process
    if proc.mode != "balanced" or proc.nlp_parser != "auto" or proc.autonomous_max_rounds != 8:
        lines.append("")
        lines.append("process {")
        lines.append(f'  mode: "{proc.mode}";')
        lines.append(f'  nlp_parser: "{proc.nlp_parser}";')
        lines.append(f"  nlp_confidence_min: {proc.nlp_confidence_min};")
        if proc.nlp_enrich_missing:
            lines.append("  nlp_enrich_missing: true;")
        lines.append(f'  llm_reasoning: "{proc.llm_reasoning}";')
        if proc.llm_temperature is not None:
            lines.append(f"  llm_temperature: {proc.llm_temperature};")
        if not proc.autonomous_enabled:
            lines.append("  autonomous: false;")
        if proc.autonomous_max_rounds != 8:
            lines.append(f"  autonomous_max_rounds: {proc.autonomous_max_rounds};")
        if proc.ask_user != "when_exhausted":
            lines.append(f'  ask_user: "{proc.ask_user}";')
        if proc.intract_gate:
            lines.append("  intract_gate: true;")
        if proc.intract_enforce_clarification:
            lines.append("  intract_enforce_clarification: true;")
        lines.append("}")

    if proc.agent or proc.allow_resource_areas or proc.deny_resource_areas:
        lines.append("")
        lines.append("process_access {")
        if proc.agent:
            lines.append(f'  agent: "{proc.agent}";')
        if proc.allow_resource_areas:
            lines.append(f'  allow_areas: "{",".join(proc.allow_resource_areas)}";')
        if proc.deny_resource_areas:
            lines.append(f'  deny_areas: "{",".join(proc.deny_resource_areas)}";')
        lines.append("}")

    if proc.paths_read or proc.paths_write:
        lines.append("")
        lines.append("paths {")
        if proc.paths_read:
            lines.append(f'  read: "{",".join(proc.paths_read)}";')
        if proc.paths_write:
            lines.append(f'  write: "{",".join(proc.paths_write)}";')
        lines.append("}")

    lines.append("")
    lines.append("conversation {")
    lines.append(f"  autofill: {'true' if ctx.autofill else 'false'};")
    lines.append(f"  sync_auto_execute: {'true' if ctx.sync_auto_execute else 'false'};")
    if ctx.attachment_required:
        lines.append("  attachment_required: true;")
    lines.append(
        f"  generate_invoice_if_missing: {'true' if ctx.generate_invoice_if_missing else 'false'};"
    )
    if ctx.strict_pdf:
        lines.append("  strict_pdf: true;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def write_doql_context(path: Path | str, ctx: DoqlTaskContext) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_doql_context(ctx), encoding="utf-8")
    return path
