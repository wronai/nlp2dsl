"""Bootstrap examples: UTF-8 + artifact writer env (import before scenario)."""

from __future__ import annotations

import os
from pathlib import Path


def bootstrap(example_dir: Path | str, *, title: str = "") -> Path:
    """
    Call at the start of examples/*/main.py with Path(__file__).resolve().parent.

    Sets NLP2DSL_EXAMPLE_DIR so preview/scenarios write .nlp2dsl/ artifacts.
    """
    from nlp2dsl_sdk.encoding import configure_utf8

    configure_utf8(force=True)

    root = Path(example_dir).resolve()
    os.environ["NLP2DSL_EXAMPLE_DIR"] = str(root)
    if title:
        os.environ["NLP2DSL_EXAMPLE_TITLE"] = title
    elif "NLP2DSL_EXAMPLE_TITLE" not in os.environ:
        os.environ["NLP2DSL_EXAMPLE_TITLE"] = root.name

    return root
