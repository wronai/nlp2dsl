"""Locate bundled and override data files for nlp2cmd-intent."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
from typing import Optional


def get_user_config_dir() -> Path:
    explicit = os.environ.get("NLP2CMD_CONFIG_DIR")
    if explicit:
        return Path(explicit).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "nlp2cmd"
    return Path.home() / ".config" / "nlp2cmd"


def _package_data_dir() -> Path:
    try:
        return Path(resources.files("nlp2cmd_intent").joinpath("data"))
    except Exception:
        return Path(__file__).resolve().parent / "data"


def _nlp2cmd_data_dir() -> Path | None:
    try:
        return Path(resources.files("nlp2cmd").joinpath("data"))
    except Exception:
        return None


def bundled_data_file(filename: str) -> Path | None:
    """Return a bundled package data file path, independent of external discovery."""
    path = _package_data_dir() / filename
    return path if path.exists() else None


def find_data_files(
    *,
    explicit_path: Optional[str],
    default_filename: str,
    alt_filenames: tuple[str, ...] = (),
) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if path.exists() and path not in seen:
            seen.add(path)
            out.append(path)

    names = (default_filename, *alt_filenames)
    pkg_data = _package_data_dir()
    for name in names:
        add(pkg_data / name)

    nlp2cmd_data = _nlp2cmd_data_dir()
    if nlp2cmd_data is not None:
        for name in names:
            add(nlp2cmd_data / name)

    for name in names:
        add(Path("data") / name)
        add(Path.home() / ".nlp2cmd" / name)
        add(get_user_config_dir() / name)

    if explicit_path:
        add(Path(explicit_path).expanduser())

    return out
