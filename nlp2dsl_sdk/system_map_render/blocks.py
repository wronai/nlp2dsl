"""Render individual DOQL blocks from SystemMapIR."""

from __future__ import annotations

from datetime import datetime, timezone

from ..system_map_ir import SystemMapIR
from .helpers import (
    bool_lit,
    data_value_line,
    esc_str,
    esc_str_full,
    history_value_line,
    join_csv,
    process_field_line,
)


def render_header(ir: SystemMapIR) -> list[str]:
    return [
        f"// DOQL system map — {ir.example_id}",
        "// role: LLM-generated schema (SystemMapIR → DOQL)",
        f"// format: {ir.format}",
        f"// generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]


def render_environment_block(ir: SystemMapIR) -> list[str]:
    lines = [f'environment[name="{ir.example_id}"] {{']
    for key in sorted(ir.environment):
        lines.append(f'  {key}: "{esc_str(str(ir.environment[key]))}";')
    lines.extend(["}", ""])
    return lines


def render_data_block(ir: SystemMapIR) -> list[str]:
    if not ir.data:
        return []
    lines = ["data {"]
    for key in sorted(ir.data):
        lines.append(data_value_line(key, ir.data[key]))
    lines.extend(["}", ""])
    return lines


def render_artifacts_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
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
        lines.extend(["}", ""])
    return lines


def render_runtimes_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
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
            lines.append(f'  roles: "{join_csv(rt.roles)}";')
        lines.append(f'  status: "{rt.status}";')
        lines.extend(["}", ""])
    return lines


def render_commands_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, cmd in enumerate(ir.commands):
        lines.append(f"commands[{idx}] {{")
        lines.append(f'  name: "{cmd.name}";')
        if cmd.description:
            lines.append(f'  description: "{esc_str(cmd.description)}";')
        if cmd.required_names:
            lines.append(f'  required: "{join_csv(cmd.required_names)}";')
        if cmd.optional_names:
            lines.append(f'  optional: "{join_csv(cmd.optional_names)}";')
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
        lines.extend(["}", ""])
    return lines


def render_resources_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, res in enumerate(ir.resources):
        lines.append(f"resources[{idx}] {{")
        lines.append(f'  id: "{res.id}";')
        if res.title:
            lines.append(f'  title: "{esc_str(res.title)}";')
        if res.connector:
            lines.append(f'  connector: "{res.connector}";')
        if res.uri_patterns:
            lines.append(f'  uri_patterns: "{join_csv(res.uri_patterns)}";')
        lines.extend(["}", ""])
    return lines


def render_access_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, grant in enumerate(ir.access):
        lines.append(f"access[{idx}] {{")
        lines.append(f'  agent: "{grant.agent}";')
        if grant.resource_area:
            lines.append(f'  resource_area: "{grant.resource_area}";')
        if grant.actions:
            lines.append(f'  actions: "{join_csv(grant.actions)}";')
        lines.append(f'  effect: "{grant.effect}";')
        lines.extend(["}", ""])
    return lines


def render_capabilities_block(ir: SystemMapIR) -> list[str]:
    if not ir.capabilities:
        return []
    return [
        "capabilities {",
        f'  actions: "{join_csv(ir.capabilities)}";',
        "}",
        "",
    ]


def render_workflow_history_block(ir: SystemMapIR) -> list[str]:
    if not ir.workflow_history:
        return []
    lines = ["workflow_history {"]
    for key in sorted(ir.workflow_history):
        lines.append(history_value_line(key, ir.workflow_history[key]))
    lines.extend(["}", ""])
    return lines


def render_conversation_block(ir: SystemMapIR) -> list[str]:
    conv = ir.conversation
    lines = [
        "conversation {",
        f"  autofill: {bool_lit(conv.autofill)};",
        f"  sync_auto_execute: {bool_lit(conv.sync_auto_execute)};",
    ]
    if conv.attachment_required:
        lines.append("  attachment_required: true;")
    lines.append(
        f"  generate_invoice_if_missing: {bool_lit(conv.generate_invoice_if_missing)};"
    )
    if conv.strict_pdf:
        lines.append("  strict_pdf: true;")
    lines.extend(["}", ""])
    return lines


def render_process_block(ir: SystemMapIR) -> list[str]:
    proc = ir.process
    lines = ["process {"]
    for key, val in (
        ("mode", proc.mode),
        ("nlp_parser", proc.nlp_parser),
        ("nlp_confidence_min", proc.nlp_confidence_min),
        ("nlp_enrich_missing", proc.nlp_enrich_missing),
        ("llm_reasoning", proc.llm_reasoning),
        ("autonomous", proc.autonomous_enabled),
        ("autonomous_max_rounds", proc.autonomous_max_rounds),
        ("ask_user", proc.ask_user),
        ("intract_gate", proc.intract_gate),
        ("intract_enforce_clarification", proc.intract_enforce_clarification),
    ):
        lines.append(process_field_line(key, val))
    if proc.llm_temperature is not None:
        lines.append(f"  llm_temperature: {proc.llm_temperature};")
    lines.extend(["}", ""])
    return lines


def render_process_access_block(ir: SystemMapIR) -> list[str]:
    acc = ir.process.access
    if not (acc.agent or acc.allow_resource_areas or acc.deny_resource_areas):
        return []
    lines = ["process_access {"]
    if acc.agent:
        lines.append(f'  agent: "{acc.agent}";')
    if acc.allow_resource_areas:
        lines.append(f'  allow_areas: "{join_csv(acc.allow_resource_areas)}";')
    if acc.deny_resource_areas:
        lines.append(f'  deny_areas: "{join_csv(acc.deny_resource_areas)}";')
    lines.extend(["}", ""])
    return lines


def render_paths_block(ir: SystemMapIR) -> list[str]:
    paths = ir.process.paths
    if not (paths.read or paths.write):
        return []
    lines = ["paths {"]
    if paths.read:
        lines.append(f'  read: "{join_csv(paths.read)}";')
    if paths.write:
        lines.append(f'  write: "{join_csv(paths.write)}";')
    lines.extend(["}", ""])
    return lines


def render_schedules_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, sched in enumerate(ir.schedules):
        lines.append(f"schedules[{idx}] {{")
        lines.append(f'  id: "{sched.id}";')
        lines.append(f'  cron: "{sched.cron}";')
        lines.append(f'  task: "{esc_str_full(sched.task)}";')
        if sched.workflow_action:
            lines.append(f'  workflow_action: "{sched.workflow_action}";')
        lines.append(f"  enabled: {bool_lit(sched.enabled)};")
        lines.append(f'  timezone: "{sched.timezone}";')
        lines.extend(["}", ""])
    return lines


def render_deploy_block(ir: SystemMapIR) -> list[str]:
    if not ir.deploy:
        return []
    dep = ir.deploy
    lines = [
        "deploy {",
        f'  target: "{dep.target}";',
        f'  platform_compose: "{dep.platform_compose}";',
        f'  mocks_compose: "{dep.mocks_compose}";',
        f'  stack_compose: "{dep.stack_compose}";',
    ]
    if dep.docker_profiles:
        lines.append(f'  docker_profiles: "{join_csv(dep.docker_profiles)}";')
    lines.extend(
        [
            f'  cron_service: "{dep.cron_service}";',
            f'  cron_image: "{dep.cron_image}";',
            "}",
            "",
        ]
    )
    return lines


def render_generated_services_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, svc in enumerate(ir.generated_services):
        lines.append(f"generated_services[{idx}] {{")
        lines.append(f'  name: "{svc.name}";')
        if svc.description:
            lines.append(f'  description: "{esc_str(svc.description)}";')
        if svc.image:
            lines.append(f'  image: "{svc.image}";')
        if svc.build_context:
            lines.append(f'  build_context: "{svc.build_context}";')
        if svc.roles:
            lines.append(f'  roles: "{join_csv(svc.roles)}";')
        lines.extend(["}", ""])
    return lines


def render_validations_block(ir: SystemMapIR) -> list[str]:
    lines: list[str] = []
    for idx, spec in enumerate(ir.validations):
        lines.append(f"validations[{idx}] {{")
        lines.append(f'  code: "{spec.code}";')
        if spec.action:
            lines.append(f'  action: "{spec.action}";')
        if spec.status:
            lines.append(f'  status: "{spec.status}";')
        if spec.path:
            lines.append(f'  path: "{esc_str(spec.path)}";')
        lines.extend(["}", ""])
    return lines
