"""
DOQL registry — refresh environment.doql.less after each process step.

environment.doql.less is the live source of truth: data, workflow_history,
and observations merge back after preflight, DSL ready, and execution.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from .doql_context import load_doql_context
from .invoice_policy import is_invoice_example
from .system_map_ir import SystemMapIR
from .system_map_bridge import task_context_to_system_map
from .system_map_render import render_system_map_doql


def entities_to_data(intent: str | None, entities: Mapping[str, Any]) -> dict[str, Any]:
    """Map conversation entities → DOQL data keys."""
    out: dict[str, Any] = {}
    action = intent or "send_invoice"
    for key, value in entities.items():
        if value is None or str(key).startswith("_"):
            continue
        out[f"{action}.{key}"] = value
        out.setdefault(key, value)
    return out


def merge_execution_observation(
    ir_data: dict[str, Any],
    workflow_history: dict[str, Any],
    execution: Mapping[str, Any],
    *,
    phase: str = "execute",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge worker/backend execution result into registry fields."""
    data = dict(ir_data)
    history = dict(workflow_history)

    _merge_execution_header(history, execution, phase=phase)
    for step in _execution_steps(execution):
        _merge_execution_step(data, history, step)
    _merge_workflow_id(history, execution)

    return data, history


def _merge_execution_header(
    history: dict[str, Any],
    execution: Mapping[str, Any],
    *,
    phase: str,
) -> None:
    history["last_phase"] = phase
    history["last_observed_at"] = datetime.now(UTC).isoformat()
    history["last_status"] = str(execution.get("status", execution.get("state", "")))


def _execution_steps(execution: Mapping[str, Any]) -> list[Any]:
    raw = execution.get("results") or execution.get("steps") or []
    return raw if isinstance(raw, list) else []


def _merge_execution_step(
    data: dict[str, Any],
    history: dict[str, Any],
    step: Any,
) -> None:
    if not isinstance(step, dict):
        return
    action = str(step.get("action", ""))
    output = _step_output(step)
    if action == "send_invoice":
        _merge_send_invoice_output(data, history, output)
    elif action == "generate_invoice":
        _merge_generate_invoice_output(data, output)


def _step_output(step: Mapping[str, Any]) -> dict[str, Any]:
    output = step.get("output") or step.get("result") or {}
    return output if isinstance(output, dict) else {"value": output}


def _merge_send_invoice_output(
    data: dict[str, Any],
    history: dict[str, Any],
    output: Mapping[str, Any],
) -> None:
    inv_id = output.get("invoice_id") or output.get("id")
    if not inv_id:
        return
    data["send_invoice.last_invoice_id"] = inv_id
    history["last_invoice_id"] = str(inv_id)


def _merge_generate_invoice_output(
    data: dict[str, Any],
    output: Mapping[str, Any],
) -> None:
    path = output.get("path") or output.get("output_path")
    if not path:
        return
    data["send_invoice.attachment_path"] = path
    data["attachment_path"] = path


def _merge_workflow_id(history: dict[str, Any], execution: Mapping[str, Any]) -> None:
    wf_id = execution.get("workflow_id") or execution.get("id")
    if wf_id:
        history["last_workflow_id"] = str(wf_id)


def merge_registry_observations(
    ir: SystemMapIR,
    path: Path | str,
    *,
    preserve_data_prefixes: tuple[str, ...] = ("send_invoice.",),
) -> SystemMapIR:
    """
    Merge live registry observations from an existing DOQL file into IR.

    Preserves workflow_history observation keys and selected data fields so
    finalize()/bootstrap does not wipe client-side registry updates.
    """
    path = Path(path)
    if not path.is_file():
        return ir

    ctx = load_doql_context(path)
    observation_keys = (
        "last_phase",
        "last_observed_at",
        "last_intent",
        "last_status",
        "last_invoice_id",
        "last_workflow_id",
        "conversation_id",
    )
    for key in observation_keys:
        if key in ctx.workflow_history:
            ir.workflow_history[key] = ctx.workflow_history[key]

    for key, value in ctx.data.items():
        if is_invoice_example(ir.example_id) and key in (
            "attachment_path",
            "send_invoice.attachment_path",
        ):
            continue
        if any(key.startswith(prefix) for prefix in preserve_data_prefixes):
            ir.data.setdefault(key, value)
        elif key.endswith(".last_invoice_id") or key == "attachment_path":
            ir.data.setdefault(key, value)

    return ir


def refresh_doql_registry(
    path: Path | str,
    *,
    intent: str | None = None,
    entities: Mapping[str, Any] | None = None,
    execution: Mapping[str, Any] | None = None,
    phase: str = "observe",
    extra_data: Mapping[str, Any] | None = None,
) -> Path:
    """
    Reload SystemMapIR from DOQL, merge observations, write back.
    Preserves runtimes/commands/resources from the file.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    if path.parent.name == "registry":
        example_dir = path.parent.parent.parent
    else:
        example_dir = path.parent.parent
    ctx = load_doql_context(path)
    ir = task_context_to_system_map(ctx, example_dir=example_dir)

    if entities:
        ir.data.update(entities_to_data(intent, entities))
    if extra_data:
        ir.data.update(dict(extra_data))

    ir.workflow_history.setdefault("last_phase", phase)
    ir.workflow_history["last_observed_at"] = datetime.now(UTC).isoformat()
    if intent:
        ir.workflow_history["last_intent"] = intent

    if execution:
        ir.data, ir.workflow_history = merge_execution_observation(
            ir.data,
            ir.workflow_history,
            execution,
            phase=phase,
        )

    ir.metadata["registry_source"] = "doql_registry.refresh"
    ir.metadata["last_phase"] = phase

    content = render_system_map_doql(ir)
    artifact_root_path = path.parent if path.parent.name != "registry" else path.parent.parent
    if artifact_root_path.name == ".nlp2dsl" or (artifact_root_path / "registry").is_dir():
        from .artifact_layout import write_registry

        return write_registry(artifact_root_path, content)
    path.write_text(content, encoding="utf-8")
    return path


def refresh_doql_registry_from_state(
    path: Path | str,
    *,
    intent: str | None,
    entities: Mapping[str, Any],
    phase: str,
    execution: Mapping[str, Any] | None = None,
) -> Path:
    return refresh_doql_registry(
        path,
        intent=intent,
        entities=entities,
        execution=execution,
        phase=phase,
    )
