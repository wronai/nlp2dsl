#!/usr/bin/env python3
"""
Przykład tworzenia zaplanowanych raportów z różnymi harmonogramami.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nlp2dsl_sdk import run_scheduled_report_demo


def main() -> None:
    """Główna funkcja przykładu."""

    run_scheduled_report_demo()


if __name__ == "__main__":
    main()
