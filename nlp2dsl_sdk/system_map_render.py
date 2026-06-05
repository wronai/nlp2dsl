"""Render SystemMapIR → environment.doql.less (DOQL system map)."""

from __future__ import annotations

from datetime import datetime, timezone

from .system_map_ir import SystemMapIR


def render_system_map_doql(ir: SystemMapIR) -> str:
    lines = [
        f"// DOQL system map — {ir.example_id}",
        "// role: LLM-generated schema (SystemMapIR → DOQL)",
        f"// format: {ir.format}",
        f"// generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f'environment[name="{ir.example_id}"] {{',
    ]
    for key in sorted(ir.environment):
        safe = str(ir.environment[key]).replace('"', '\\"')
        lines.append(f'  {key}: "{safe}";')
    lines.append("}")
    lines.append("")

    if ir.data:
        lines.append("data {")
        for key in sorted(ir.data):
            val = ir.data[key]
            if isinstance(val, str):
                safe = val.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'  {key}: "{safe}";')
            elif isinstance(val, bool):
                lines.append(f"  {key}: {'true' if val else 'false'};")
            else:
                lines.append(f"  {key}: {val};")
        lines.append("}")
        lines.append("")

    for idx, art in enumerate(ir.artifacts):
        lines.append(f"artifacts[{idx}] {{")
        lines.append(f'  path: "{art.path}";')
        lines.append(f'  kind: "{art.kind}";')
        if art.mime:
            lines.append(f'  mime: "{art.mime.type}";')
            if art.mime.schema_ref:
                lines.append(f'  schema_ref: "{art.mime.schema_ref}";')
        for k, v in sorted(art.values.items()):
            if isinstance(v, str):
                lines.append(f'  {k}: "{v}";')
            else:
                lines.append(f"  {k}: {v};")
        lines.append("}")
        lines.append("")

    for idx, rt in enumerate(ir.runtimes):
        lines.append(f"runtimes[{idx}] {{")
        lines.append(f'  id: "{rt.id}";')
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
        lines.append(f'  status: "{rt.status}";')
        lines.append("}")
        lines.append("")

    for idx, cmd in enumerate(ir.commands):
        lines.append(f"commands[{idx}] {{")
        lines.append(f'  name: "{cmd.name}";')
        if cmd.description:
            safe = cmd.description.replace('"', '\\"')
            lines.append(f'  description: "{safe}";')
        if cmd.required_names:
            lines.append(f'  required: "{",".join(cmd.required_names)}";')
        if cmd.optional_names:
            lines.append(f'  optional: "{",".join(cmd.optional_names)}";')
        if cmd.input_model:
            lines.append(f'  input_model: "{cmd.input_model}";')
        if cmd.runtime:
            lines.append(f'  runtime: "{cmd.runtime}";')
        proto = cmd.protocol
        if proto.transport:
            lines.append(f'  transport: "{proto.transport}";')
        if proto.endpoint:
            lines.append(f'  endpoint: "{proto.endpoint}";')
        lines.append(f'  protocol: "{proto.name}";')
        lines.append("}")
        lines.append("")

    for idx, res in enumerate(ir.resources):
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

    for idx, grant in enumerate(ir.access):
        lines.append(f"access[{idx}] {{")
        lines.append(f'  agent: "{grant.agent}";')
        if grant.resource_area:
            lines.append(f'  resource_area: "{grant.resource_area}";')
        if grant.actions:
            lines.append(f'  actions: "{",".join(grant.actions)}";')
        lines.append(f'  effect: "{grant.effect}";')
        lines.append("}")
        lines.append("")

    if ir.capabilities:
        lines.append("capabilities {")
        lines.append(f'  actions: "{",".join(ir.capabilities)}";')
        lines.append("}")
        lines.append("")

    if ir.workflow_history:
        lines.append("workflow_history {")
        for key in sorted(ir.workflow_history):
            val = ir.workflow_history[key]
            if isinstance(val, list):
                lines.append(f'  {key}: "{",".join(str(v) for v in val)}";')
            elif isinstance(val, str):
                lines.append(f'  {key}: "{val}";')
            else:
                lines.append(f"  {key}: {val};")
        lines.append("}")
        lines.append("")

    conv = ir.conversation
    lines.append("conversation {")
    lines.append(f"  autofill: {'true' if conv.autofill else 'false'};")
    lines.append(f"  sync_auto_execute: {'true' if conv.sync_auto_execute else 'false'};")
    lines.append(f"  attachment_required: {'true' if conv.attachment_required else 'false'};")
    lines.append(
        f"  generate_invoice_if_missing: {'true' if conv.generate_invoice_if_missing else 'false'};"
    )
    lines.append("}")
    lines.append("")

    for idx, sched in enumerate(ir.schedules):
        lines.append(f"schedules[{idx}] {{")
        lines.append(f'  id: "{sched.id}";')
        lines.append(f'  cron: "{sched.cron}";')
        safe_task = sched.task.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'  task: "{safe_task}";')
        if sched.workflow_action:
            lines.append(f'  workflow_action: "{sched.workflow_action}";')
        lines.append(f"  enabled: {'true' if sched.enabled else 'false'};")
        lines.append(f'  timezone: "{sched.timezone}";')
        lines.append("}")
        lines.append("")

    if ir.deploy:
        dep = ir.deploy
        lines.append("deploy {")
        lines.append(f'  target: "{dep.target}";')
        lines.append(f'  platform_compose: "{dep.platform_compose}";')
        lines.append(f'  mocks_compose: "{dep.mocks_compose}";')
        lines.append(f'  stack_compose: "{dep.stack_compose}";')
        if dep.docker_profiles:
            lines.append(f'  docker_profiles: "{",".join(dep.docker_profiles)}";')
        lines.append(f'  cron_service: "{dep.cron_service}";')
        lines.append(f'  cron_image: "{dep.cron_image}";')
        lines.append("}")
        lines.append("")

    for idx, svc in enumerate(ir.generated_services):
        lines.append(f"generated_services[{idx}] {{")
        lines.append(f'  name: "{svc.name}";')
        if svc.description:
            safe = svc.description.replace('"', '\\"')
            lines.append(f'  description: "{safe}";')
        if svc.image:
            lines.append(f'  image: "{svc.image}";')
        if svc.build_context:
            lines.append(f'  build_context: "{svc.build_context}";')
        if svc.roles:
            lines.append(f'  roles: "{",".join(svc.roles)}";')
        lines.append("}")
        lines.append("")

    return "\n".join(lines)
