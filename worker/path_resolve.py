"""Worker attachment path resolution (examples mount + fixtures)."""

from __future__ import annotations

import os
from pathlib import Path

from nlp2dsl_sdk.path_resolve import resolve_attachment_path


def resolve_worker_attachment_path(raw: str) -> str:
    """Resolve attachment path using worker env (examples mount + fixtures)."""
    if not raw:
        return raw
    path = Path(raw)
    if path.is_file():
        return str(path.resolve())

    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        ex = Path(example_dir)
        for candidate in (ex / raw, ex / "fixtures" / path.name):
            if candidate.is_file():
                return str(candidate.resolve())

    os.environ.setdefault("NLP2DSL_EXAMPLES_MOUNT", "/examples")
    return resolve_attachment_path(raw)
