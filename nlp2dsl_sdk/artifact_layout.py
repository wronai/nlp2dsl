"""
Layout for examples/*/.nlp2dsl/ — registry, per-run turn snapshots, reports.

  .nlp2dsl/
    registry/environment.doql.less   ← live process state (single source of truth)
    runs/{run_id}/turn-NN-{phase}.json
    report/last-run.result.json
    pipeline/ …                    ← per-query debug (unchanged)
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

# Static inputs checked into or hand-maintained under examples/*/.nlp2dsl/
_PRESERVED_ROOT_FILES = frozenset(
    {
        "conversation.scenario.yaml",
        "conversation.llm.scenario.yaml",
        "conversation.attachment.scenario.yaml",
        "conversation.testql.toon.yaml",
        "execution.scenario.yaml",
        "execution.llm.scenario.yaml",
    }
)
_PRESERVED_DIRS = frozenset({"fixtures"})

REGISTRY_REL = Path("registry") / "environment.doql.less"
LEGACY_REGISTRY_REL = Path("environment.doql.less")
RUNS_DIR = Path("runs")
REPORT_DIR = Path("report")
LAST_RUN_RESULT = Path("report") / "last-run.result.json"


def artifact_root(example_dir: Path | str) -> Path:
    return Path(example_dir).resolve() / ".nlp2dsl"


def _chmod_writable(path: os.PathLike[str] | str) -> None:
    try:
        os.chmod(path, stat.S_IWUSR | stat.S_IREAD | stat.S_IEXEC)
    except OSError:
        pass


def _force_remove_path(path: Path) -> bool:
    """Remove a file or tree; chmod root-owned Docker artifacts when possible."""

    if not path.exists():
        return True

    if path.is_dir():
        for root, dirs, files in os.walk(path, topdown=False):
            for name in list(files) + list(dirs):
                _chmod_writable(Path(root) / name)
            _chmod_writable(root)

    def _onexc(func, target, exc):
        if isinstance(exc, PermissionError):
            _chmod_writable(target)
            try:
                func(target)
            except OSError:
                return
            return
        raise exc

    try:
        if path.is_dir():
            shutil.rmtree(path, onexc=_onexc)
        else:
            path.unlink()
    except OSError:
        return False
    return not path.exists()


def clean_artifact_root(
    example_dir: Path | str,
    *,
    preserve_sources: bool = True,
) -> list[Path]:
    """Remove generated artifacts under ``examples/*/.nlp2dsl`` before a fresh run.

    Preserves hand-maintained scenario/fixture files (``fixtures/``, ``*.scenario.yaml``).
    """
    root = artifact_root(example_dir)
    if not root.is_dir():
        return []

    removed: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda path: (not path.is_dir(), path.name)):
        if preserve_sources:
            if child.is_dir() and child.name in _PRESERVED_DIRS:
                continue
            if child.is_file() and child.name in _PRESERVED_ROOT_FILES:
                continue
        if _force_remove_path(child):
            removed.append(child)
    return removed


def clean_all_example_artifacts(
    examples_dir: Path | str,
    *,
    preserve_sources: bool = True,
) -> dict[str, list[str]]:
    """Clean ``.nlp2dsl/`` for every ``examples/*/`` directory."""
    base = Path(examples_dir).resolve()
    cleaned: dict[str, list[str]] = {}
    for example_dir in sorted(base.iterdir()):
        if not example_dir.is_dir():
            continue
        removed = clean_artifact_root(example_dir, preserve_sources=preserve_sources)
        if removed:
            cleaned[example_dir.name] = [path.name for path in removed]
    return cleaned


def example_fixtures_dir(example_dir: Path | str) -> Path:
    """Static fixtures outside generated .nlp2dsl (not removed on clean)."""
    return Path(example_dir).resolve() / "fixtures"


def ensure_layout(root: Path | str) -> Path:
    """Create registry/, runs/, report/ under .nlp2dsl. Returns registry path."""
    base = Path(root).resolve()
    base.mkdir(parents=True, exist_ok=True)
    (base / "registry").mkdir(parents=True, exist_ok=True)
    (base / "runs").mkdir(parents=True, exist_ok=True)
    (base / "report").mkdir(parents=True, exist_ok=True)
    return base / REGISTRY_REL


def resolve_registry_path(
    *,
    explicit: str | Path | None = None,
    example_dir: str | Path | None = None,
) -> Path | None:
    """Resolve live DOQL registry file (registry/ first, legacy root fallback)."""
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path

    raw = os.environ.get("NLP2DSL_DOQL_CONTEXT", "").strip()
    if raw:
        path = Path(raw)
        if path.is_file():
            return path

    ex = example_dir or os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if ex:
        root = artifact_root(ex)
        primary = root / REGISTRY_REL
        if primary.is_file():
            return primary
        legacy = root / LEGACY_REGISTRY_REL
        if legacy.is_file():
            return legacy
    return None


def write_registry(root: Path | str, content: str) -> Path:
    """Write DOQL to registry/ and mirror legacy path for backward compatibility."""
    base = Path(root).resolve()
    ensure_layout(base)
    primary = base / REGISTRY_REL
    primary.write_text(content, encoding="utf-8")
    legacy = base / LEGACY_REGISTRY_REL
    if legacy != primary:
        legacy.write_text(content, encoding="utf-8")
    return primary


def current_run_id(root: Path | str) -> str:
    env = os.environ.get("NLP2DSL_RUN_ID", "").strip()
    if env:
        return env
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    os.environ["NLP2DSL_RUN_ID"] = stamp
    return stamp


def run_dir(root: Path | str, run_id: str | None = None) -> Path:
    base = Path(root).resolve()
    rid = run_id or current_run_id(base)
    path = base / RUNS_DIR / rid
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_turn_snapshot(
    artifact_root_path: Path | str,
    *,
    turn: int,
    phase: str,
    response: Mapping[str, Any],
    registry_path: Path | None = None,
    run_id: str | None = None,
) -> Path:
    """Persist one conversation turn under runs/{run_id}/."""
    base = Path(artifact_root_path).resolve()
    out_dir = run_dir(base, run_id)
    safe_phase = phase.replace("/", "-").replace(" ", "_")[:40]
    filename = f"turn-{turn:02d}-{safe_phase}.json"
    payload: dict[str, Any] = {
        "turn": turn,
        "phase": phase,
        "status": response.get("status"),
        "generated_at": datetime.now(UTC).isoformat(),
        "conversation_id": response.get("conversation_id"),
        "missing": response.get("missing"),
        "autofill_applied": response.get("autofill_applied"),
        "dsl": response.get("dsl"),
        "execution": response.get("execution"),
        "attachment_validation": response.get("attachment_validation"),
    }
    if registry_path and registry_path.is_file():
        payload["registry_path"] = str(registry_path.name)
        try:
            from .doql_context import load_doql_context

            ctx = load_doql_context(registry_path)
            payload["registry_observation"] = {
                "data": dict(ctx.data),
                "workflow_history": dict(ctx.workflow_history),
            }
        except Exception:
            pass

    out_path = out_dir / filename
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def write_reflection_snapshot(
    artifact_root_path: Path | str,
    *,
    turn: int,
    phase: str,
    report: Mapping[str, Any],
    run_id: str | None = None,
) -> Path:
    """Persist reflection report under runs/{run_id}/reflect-NN-{phase}.json."""
    base = Path(artifact_root_path).resolve()
    out_dir = run_dir(base, run_id)
    safe_phase = phase.replace("/", "-").replace(" ", "_")[:40]
    filename = f"reflect-{turn:02d}-{safe_phase}.json"
    out_path = out_dir / filename
    out_path.write_text(json.dumps(dict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def write_last_run_report(root: Path | str, payload: Mapping[str, Any]) -> Path:
    base = Path(root).resolve()
    ensure_layout(base)
    path = base / LAST_RUN_RESULT
    path.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
