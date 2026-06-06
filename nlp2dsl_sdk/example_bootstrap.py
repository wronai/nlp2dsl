"""Bootstrap DOQL registry — delegates to :mod:`env2llm.bootstrap`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from env2llm.bootstrap import ensure_environment_map


def ensure_doql_registry(
    example_dir: Path | str,
    *,
    example_id: str | None = None,
    environment: Mapping[str, str] | None = None,
    attachment: bool | None = None,
    auto_execute: bool | None = None,
) -> Path:
    """Bootstrap or refresh registry/environment.doql.less from SystemMapIR."""
    return ensure_environment_map(
        example_dir,
        project_id=example_id,
        environment=environment,
        attachment=attachment,
        auto_execute=auto_execute,
    )


__all__ = ["ensure_doql_registry"]
