#!/usr/bin/env python3
"""
Example usage of multi-language code generation via API.

This demonstrates how to use the generate_code action through the nlp2dsl API.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nlp2dsl_sdk import run_code_generation_demo


def main() -> None:
    """Run the code generation showcase via the shared SDK."""

    run_code_generation_demo()


if __name__ == "__main__":
    main()
