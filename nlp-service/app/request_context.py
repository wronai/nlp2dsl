"""Per-request context (example dir for fixture path resolution in Docker)."""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

_example_dir: ContextVar[str | None] = ContextVar("nlp2dsl_example_dir", default=None)


def set_example_dir(path: str | Path | None) -> None:
    if path is None:
        _example_dir.set(None)
        return
    raw = str(path).strip()
    _example_dir.set(raw or None)


def get_example_dir() -> Path | None:
    raw = _example_dir.get()
    if raw:
        return Path(raw).resolve()
    return None
