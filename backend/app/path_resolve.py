"""Resolve attachment_path relative to example dir / DOQL."""

from __future__ import annotations

import os
from pathlib import Path


def _examples_portable_candidates(raw: str) -> list[Path]:
    norm = str(raw).replace("\\", "/")
    rel: str | None = None
    mount = os.environ.get("NLP2DSL_EXAMPLES_MOUNT", "/examples").strip().rstrip("/")
    if mount and norm.startswith(f"{mount}/"):
        rel = norm[len(mount) + 1 :]
    elif norm.startswith("/examples/"):
        rel = norm[len("/examples/") :]
    if not rel or "/" not in rel:
        return []
    ex_name, rest = rel.split("/", 1)
    candidates: list[Path] = []
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        candidates.append(Path(example_dir) / rest)
    cwd = Path.cwd()
    for base in (cwd, cwd.parent, cwd.parent.parent):
        candidates.append(base / "examples" / ex_name / rest)
    return candidates


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

    candidates.extend(_examples_portable_candidates(raw))

    if doql_path:
        base = Path(doql_path).resolve().parent
        candidates.extend([base / raw, base.parent / raw])
        if base.name == "registry":
            candidates.append(base.parent / raw)

    mount = os.environ.get("NLP2DSL_EXAMPLES_MOUNT", "").strip()
    if mount and doql_path:
        parts = Path(doql_path).parts
        if "examples" in parts:
            idx = parts.index("examples")
            if idx + 1 < len(parts):
                candidates.append(Path(mount) / parts[idx + 1] / raw)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return raw
