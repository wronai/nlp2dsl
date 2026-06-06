"""Bootstrap examples: UTF-8 + artifact writer env (import before scenario)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path


def _ensure_sdk_installed(repo_root: Path) -> None:
    """Install editable nlp2dsl when the active venv lacks SDK deps (e.g. koru .venv)."""
    try:
        import pydantic  # noqa: F401
    except ImportError:
        print(f"==> Brak pydantic — instaluję nlp2dsl: pip install -e {repo_root}", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(repo_root), "-q"])


def _should_clean_artifacts() -> bool:
    raw = os.environ.get("NLP2DSL_SKIP_ARTIFACT_CLEAN", "").strip().lower()
    return raw not in {"1", "true", "yes", "on"}


def _should_clear_idempotency() -> bool:
    raw = os.environ.get("NLP2DSL_CLEAR_IDEMPOTENCY", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _try_clear_backend_idempotency(backend_url: str) -> None:
    if not _should_clear_idempotency():
        return
    try:
        import requests

        response = requests.post(
            f"{backend_url.rstrip('/')}/workflow/idempotency/clear",
            timeout=3.0,
        )
        if response.status_code == 404:
            print(
                "==> Backend bez /workflow/idempotency/clear — użyj run-scoped keys "
                "(docker compose build backend && docker compose up -d backend)",
                file=sys.stderr,
            )
            return
        response.raise_for_status()
    except Exception as exc:
        print(f"==> Nie udało się wyczyścić idempotency store: {exc}", file=sys.stderr)
        return


def bootstrap(example_dir: Path | str, *, title: str = "") -> Path:
    """
    Call at the start of examples/*/main.py with Path(__file__).resolve().parent.

    Sets NLP2DSL_EXAMPLE_DIR so preview/scenarios write .nlp2dsl/ artifacts.
    Clears generated ``.nlp2dsl/`` output (keeps fixtures/scenarios) before each run.
    """
    root = Path(example_dir).resolve()
    repo_root = root.parent.parent
    _ensure_sdk_installed(repo_root)

    from nlp2dsl_sdk.artifact_layout import clean_artifact_root
    from nlp2dsl_sdk.encoding import configure_utf8

    configure_utf8(force=True)

    if _should_clean_artifacts():
        removed = clean_artifact_root(root)
        if removed:
            print(f"==> Czyszczenie .nlp2dsl ({len(removed)} elementów)", file=sys.stderr)
        os.environ.pop("NLP2DSL_RUN_ID", None)

    os.environ["NLP2DSL_RUN_ID"] = uuid.uuid4().hex[:12]

    os.environ.setdefault("NLP2DSL_REPO_ROOT", str(repo_root))
    os.environ["NLP2DSL_EXAMPLE_DIR"] = str(root)
    backend = os.environ.get("NLP2DSL_BACKEND_URL", "http://localhost:8010")
    os.environ.setdefault("NLP2DSL_BACKEND_URL", backend)
    os.environ.setdefault("NLP2DSL_NLP_SERVICE_URL", "http://localhost:8012")
    os.environ.setdefault("NLP2DSL_WORKER_URL", "http://localhost:8004")
    if not os.environ.get("NLP2DSL_EXAMPLES_MOUNT") and "8010" in backend:
        os.environ.setdefault("NLP2DSL_EXAMPLES_MOUNT", "/examples")
    _try_clear_backend_idempotency(backend)
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
