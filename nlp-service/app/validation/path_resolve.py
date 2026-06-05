"""Resolve attachment_path relative to example dir / DOQL / fixtures."""

from __future__ import annotations

import os
from pathlib import Path

from app.request_context import get_example_dir


def resolve_attachment_path(raw: str, *, doql_path: Path | str | None = None) -> str:
    """
    Turn DOQL artifact refs (fixtures/faktura.pdf) into absolute paths when the file exists.

    Search order:
      1. as given (absolute or cwd-relative)
      2. NLP2DSL_EXAMPLE_DIR / path
      3. NLP2DSL_EXAMPLE_DIR / fixtures / basename
      4. doql file parent / path
      5. doql parent / .nlp2dsl / path
    """
    if not raw or not str(raw).strip():
        return raw

    path = Path(raw)
    if path.is_file():
        return str(path.resolve())

    candidates: list[Path] = []
    req_ex = get_example_dir()
    if req_ex:
        candidates.extend([req_ex / raw, req_ex / "fixtures" / path.name])
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
