"""Minimal .env loader for example E2E scripts (no extra dependency)."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | str, *, override: bool = False) -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = val
