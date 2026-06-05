#!/usr/bin/env python3
"""11-notify-quality"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = Path(__file__).resolve().parent
for p in (REPO_ROOT, EXAMPLES_ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from bootstrap import bootstrap

bootstrap(EXAMPLE_DIR)

from scenario import run

if __name__ == "__main__":
    run()
