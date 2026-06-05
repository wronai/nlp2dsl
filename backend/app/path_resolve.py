"""Resolve attachment_path relative to example dir / DOQL."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_attachment_path(raw: str, *, doql_path: Path | str | None = None) -> str:
    if not raw or not str(raw).strip():
        return raw

    path = Path(raw)
    if path.is_file():
        return str(path.resolve())

    candidates: list[Path] = []
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        ex = Path(example_dir)
        candidates.extend([ex / raw, ex / "fixtures" / path.name])

    if doql_path:
        base = Path(doql_path).resolve().parent
        candidates.extend([base / raw, base.parent / raw])
        if base.name == "registry":
            candidates.append(base.parent / raw)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return raw
