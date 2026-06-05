"""Dynamic Pydantic models from SystemMapIR FieldSpec + MIME types."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model

from .system_map_ir import CommandSchemaIR, FieldSpec, SystemMapIR


def _annotation_for_field(field: FieldSpec) -> tuple[type, Any]:
    if field.mime and field.mime.type == "application/pdf":
        base: type = str
    elif field.mime and field.mime.type == "application/json":
        base = dict[str, Any]
    elif field.mime and field.mime.type.startswith("text/"):
        base = str
    elif field.name in ("amount", "total", "price", "quantity"):
        base = float
    else:
        base = Any

    if field.required:
        return base, Field(description=field.description or None)
    return base | None, Field(default=None, description=field.description or None)


def command_input_model(cmd: CommandSchemaIR) -> type[BaseModel]:
    """Build a runtime Pydantic model for one command's step config."""
    model_name = cmd.input_model or "".join(part.title() for part in cmd.name.split("_")) + "Config"
    field_defs: dict[str, tuple[type, Any]] = {}
    for spec in cmd.fields:
        field_defs[spec.name] = _annotation_for_field(spec)
    return create_model(model_name, **field_defs)  # type: ignore[call-overload]


def build_command_registry(ir: SystemMapIR) -> dict[str, type[BaseModel]]:
    return {cmd.name: command_input_model(cmd) for cmd in ir.commands}


def validate_config_against_map(ir: SystemMapIR, action: str, config: dict[str, Any]) -> dict[str, Any]:
    """Validate config with dynamic model; raises ValidationError on failure."""
    cmd = ir.command(action)
    if cmd is None:
        raise ValueError(f"unknown action: {action}")
    model = command_input_model(cmd)
    return model.model_validate(config).model_dump(exclude_none=True)
