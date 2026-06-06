"""Render SystemMapIR → environment.doql.less (DOQL system map)."""

from __future__ import annotations

from ..system_map_ir import SystemMapIR
from .blocks import (
    render_access_block,
    render_artifacts_block,
    render_capabilities_block,
    render_commands_block,
    render_conversation_block,
    render_data_block,
    render_deploy_block,
    render_environment_block,
    render_generated_services_block,
    render_header,
    render_paths_block,
    render_process_access_block,
    render_process_block,
    render_resources_block,
    render_runtimes_block,
    render_schedules_block,
    render_validations_block,
    render_workflow_history_block,
)


def render_system_map_doql(ir: SystemMapIR) -> str:
    lines: list[str] = []
    lines.extend(render_header(ir))
    lines.extend(render_environment_block(ir))
    lines.extend(render_data_block(ir))
    lines.extend(render_artifacts_block(ir))
    lines.extend(render_runtimes_block(ir))
    lines.extend(render_commands_block(ir))
    lines.extend(render_resources_block(ir))
    lines.extend(render_access_block(ir))
    lines.extend(render_capabilities_block(ir))
    lines.extend(render_workflow_history_block(ir))
    lines.extend(render_conversation_block(ir))
    lines.extend(render_process_block(ir))
    lines.extend(render_process_access_block(ir))
    lines.extend(render_paths_block(ir))
    lines.extend(render_schedules_block(ir))
    lines.extend(render_deploy_block(ir))
    lines.extend(render_generated_services_block(ir))
    lines.extend(render_validations_block(ir))
    return "\n".join(lines)
