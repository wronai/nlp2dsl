"""DOQL context — SDK shim + nlp-service conversation helpers (C2)."""

from __future__ import annotations

import os
from pathlib import Path

from nlp2dsl_sdk.doql.models import (
    DoqlArtifact,
    DoqlCommand,
    DoqlProcessPolicy,
    DoqlRuntime,
    DoqlTaskContext,
)
from nlp2dsl_sdk.doql.parse import load_doql_context
from nlp2dsl_sdk.doql.runtime import autofill_entities, merge_inline_context

__all__ = [
    "DoqlArtifact",
    "DoqlCommand",
    "DoqlProcessPolicy",
    "DoqlRuntime",
    "DoqlTaskContext",
    "autofill_entities",
    "load_doql_context",
    "merge_inline_context",
    "resolve_doql_context_path",
]


def resolve_doql_context_path(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
    raw = os.environ.get("NLP2DSL_DOQL_CONTEXT", "").strip()
    if raw:
        path = Path(raw)
        if path.is_file():
            return path
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        root = Path(example_dir)
        for candidate in (
            root / ".nlp2dsl" / "registry" / "environment.doql.less",
            root / ".nlp2dsl" / "environment.doql.less",
        ):
            if candidate.is_file():
                return candidate
    from nlp2dsl_sdk.doql.runtime import resolve_doql_context_path as sdk_resolve

    return sdk_resolve()
