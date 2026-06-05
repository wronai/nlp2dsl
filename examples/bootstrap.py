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
    backend = os.environ.get("NLP2DSL_BACKEND_URL", "http://localhost:8010")
    if not os.environ.get("NLP2DSL_EXAMPLES_MOUNT") and "8010" in backend:
        os.environ.setdefault("NLP2DSL_EXAMPLES_MOUNT", "/examples")
    if title:
        os.environ["NLP2DSL_EXAMPLE_TITLE"] = title
    elif "NLP2DSL_EXAMPLE_TITLE" not in os.environ:
        os.environ["NLP2DSL_EXAMPLE_TITLE"] = root.name

    from nlp2dsl_sdk.artifact_layout import resolve_registry_path

    root = Path(example_dir).resolve()
    for candidate in (
        root / ".nlp2dsl" / "registry" / "environment.doql.less",
        root / ".nlp2dsl" / "environment.doql.less",
    ):
        if candidate.is_file() and "NLP2DSL_DOQL_CONTEXT" not in os.environ:
            os.environ["NLP2DSL_DOQL_CONTEXT"] = str(candidate)
            break
    else:
        resolved = resolve_registry_path(example_dir=root)
        if resolved and "NLP2DSL_DOQL_CONTEXT" not in os.environ:
            os.environ["NLP2DSL_DOQL_CONTEXT"] = str(resolved)

    return root
