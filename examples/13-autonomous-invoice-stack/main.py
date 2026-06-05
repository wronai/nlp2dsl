#!/usr/bin/env python3
"""Przykład 13 — autonomiczny stack faktur + docker compose + cron."""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = Path(__file__).resolve().parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_bootstrap_spec = importlib.util.spec_from_file_location(
    "examples_bootstrap", EXAMPLES_ROOT / "bootstrap.py"
)
_bootstrap = importlib.util.module_from_spec(_bootstrap_spec)
assert _bootstrap_spec.loader is not None
_bootstrap_spec.loader.exec_module(_bootstrap)
_bootstrap.bootstrap(EXAMPLE_DIR)

_scenario_spec = importlib.util.spec_from_file_location(
    f"scenario_{EXAMPLE_DIR.name.replace('-', '_')}",
    EXAMPLE_DIR / "scenario.py",
)
_scenario = importlib.util.module_from_spec(_scenario_spec)
assert _scenario_spec.loader is not None
_scenario_spec.loader.exec_module(_scenario)
run = _scenario.run

if __name__ == "__main__":
    run()
