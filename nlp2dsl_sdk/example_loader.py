"""Load run() from examples/<dir>/scenario.py for nlp2dsl-demo CLI."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from . import encoding as _encoding  # noqa: F401 — UTF-8 auto
from .client import NLP2DSLClient

_REPO_ROOT = Path(__file__).resolve().parents[1]


def load_example_runner(example_dir: str) -> Callable[[Optional[NLP2DSLClient]], Any]:
    """Import examples/<example_dir>/scenario.py and return its run() function."""

    scenario_path = _REPO_ROOT / "examples" / example_dir / "scenario.py"
    if not scenario_path.is_file():
        raise FileNotFoundError(f"Brak {scenario_path}")

    module_name = f"nlp2dsl_example_{example_dir.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, scenario_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nie można załadować {scenario_path}")

    module = importlib.util.module_from_spec(spec)
    example_str = str(scenario_path.parent)
    repo_str = str(_REPO_ROOT)
    for path in (example_str, repo_str):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec.loader.exec_module(module)

    run_fn = getattr(module, "run", None)
    if run_fn is None:
        raise AttributeError(f"{scenario_path} musi definiować funkcję run(client=None)")
    return run_fn
