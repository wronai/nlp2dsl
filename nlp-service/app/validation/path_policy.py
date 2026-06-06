"""Validate artifact paths against DOQL process.paths (read / write globs)."""

from __future__ import annotations

import re
from pathlib import Path

from app.conversation.doql_context import DoqlTaskContext
from app.request_context import get_example_dir


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    parts = [re.escape(chunk) for chunk in pattern.replace("\\", "/").split("**")]
    return re.compile("^" + ".*".join(parts) + "$")


def path_matches_glob(rel_path: str, pattern: str) -> bool:
    rel = rel_path.replace("\\", "/").lstrip("./")
    pat = pattern.replace("\\", "/").lstrip("./")
    if not pat:
        return False
    return bool(_glob_to_regex(pat).match(rel))


def example_relative_path(resolved: str | Path, example_dir: Path | None = None) -> str | None:
    ex = example_dir
    if ex is None:
        req = get_example_dir()
        if req is not None:
            ex = req
        else:
            import os

            raw = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
            ex = Path(raw).resolve() if raw else None
    if ex is None:
        return None
    try:
        return Path(resolved).resolve().relative_to(ex.resolve()).as_posix()
    except ValueError:
        return None


def path_allowed_by_patterns(rel_path: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    return any(path_matches_glob(rel_path, pat) for pat in patterns)


def validate_process_path(
    ctx: DoqlTaskContext | None,
    resolved_path: str,
    *,
    access: str = "read",
) -> str | None:
    """
    Return user-facing error when resolved path is outside process.paths scope.
    None when allowed or no paths policy configured.
    """
    if ctx is None:
        return None
    patterns = ctx.process.paths_read if access == "read" else ctx.process.paths_write
    if not patterns:
        return None

    from app.conversation.doql_context import resolve_doql_context_path
    from app.validation.path_resolve import resolve_attachment_path

    doql = resolve_doql_context_path()
    resolved_abs = resolve_attachment_path(resolved_path, doql_path=doql)
    rel = example_relative_path(resolved_abs)
    if rel is None:
        return (
            f"Ścieżka `{resolved_path}` jest poza katalogiem przykładu "
            f"(process.paths.{access})."
        )
    if path_allowed_by_patterns(rel, patterns):
        return None
    scope = ", ".join(patterns)
    return (
        f"Ścieżka `{rel}` nie mieści się w dozwolonym zakresie process.paths.{access} "
        f"({scope})."
    )
