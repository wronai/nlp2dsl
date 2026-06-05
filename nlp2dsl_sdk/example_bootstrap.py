"""Bootstrap DOQL registry for examples/* — shared by scenario scripts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from .artifact_layout import ensure_layout, write_registry
from .artifacts import collect_environment
from .doql_registry import merge_registry_observations
from .system_map_generator import generate_system_map
from .system_map_render import render_system_map_doql


def ensure_doql_registry(
    example_dir: Path | str,
    *,
    example_id: str | None = None,
    environment: Mapping[str, str] | None = None,
    attachment: bool = False,
    auto_execute: bool | None = None,
) -> Path:
    """
    Bootstrap or refresh registry/environment.doql.less from SystemMapIR.

    Preserves live observations via merge_registry_observations.
    Sets NLP2DSL_DOQL_CONTEXT when unset.
    """
    root = Path(example_dir).resolve()
    ex_id = example_id or root.name
    artifact_root = root / ".nlp2dsl"
    ensure_layout(artifact_root)

    ir = generate_system_map(
        root,
        example_id=ex_id,
        environment=dict(environment or collect_environment()),
    )
    if attachment:
        ir.conversation.attachment_required = True
        ir.conversation.generate_invoice_if_missing = True
        ir.data.pop("send_invoice.attachment_path", None)
        if "generate_invoice" not in ir.capabilities:
            ir.capabilities = sorted(set(ir.capabilities) | {"generate_invoice"})
    else:
        ir.data.pop("send_invoice.attachment_path", None)
        ir.data.pop("attachment_path", None)

    if auto_execute is None:
        auto_execute = os.environ.get("NLP2DSL_AUTO_EXECUTE", "1").strip().lower() in ("1", "true", "yes")
    if auto_execute:
        ir.conversation.sync_auto_execute = True

    merge_registry_observations(ir, artifact_root / "registry" / "environment.doql.less")
    path = write_registry(artifact_root, render_system_map_doql(ir))
    os.environ.setdefault("NLP2DSL_DOQL_CONTEXT", str(path))
    return path
