#!/usr/bin/env python3
"""
Przykład pełnego konwersacyjnego flow z platformą NLP2DSL.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nlp2dsl_sdk import ConversationFlow


def main() -> None:
    """Główna funkcja przykładu."""

    parser = argparse.ArgumentParser(description="Przykład konwersacyjnego flow")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Uruchom tryb interaktywny",
    )
    args = parser.parse_args()

    flow = ConversationFlow()

    if args.interactive:
        flow.run_interactive()
    else:
        flow.run_demo()


if __name__ == "__main__":
    main()
