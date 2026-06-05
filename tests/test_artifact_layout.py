"""Tests for .nlp2dsl layout helpers."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.artifact_layout import (
    ensure_layout,
    resolve_registry_path,
    write_registry,
    write_turn_snapshot,
)
from nlp2dsl_sdk.doql_registry import refresh_doql_registry


def test_write_registry_creates_layout(tmp_path: Path) -> None:
    root = tmp_path / ".nlp2dsl"
    path = write_registry(root, "environment[name=\"t\"] {}\n")
    assert path == root / "registry" / "environment.doql.less"
    assert path.is_file()
    assert (root / "environment.doql.less").is_file()
    assert (root / "runs").is_dir()
    assert (root / "report").is_dir()


def test_resolve_registry_path_prefers_registry(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    root = ex / ".nlp2dsl"
    ensure_layout(root)
    reg = root / "registry" / "environment.doql.less"
    reg.write_text("environment[name=\"t\"] {}\n", encoding="utf-8")
    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    assert resolve_registry_path() == reg


def test_write_environment_doql_uses_registry(tmp_path: Path) -> None:
    from nlp2dsl_sdk.artifacts import write_environment_doql

    ex = tmp_path / "01-invoice"
    root = ex / ".nlp2dsl"
    path = write_environment_doql(root, "01-invoice", {"NLP2DSL_BACKEND_URL": "http://localhost:8010"})
    assert path == root / "registry" / "environment.doql.less"
    assert path.is_file()
    assert (root / "environment.doql.less").is_file()
    text = path.read_text(encoding="utf-8")
    assert 'environment[name="01-invoice"]' in text


def test_turn_snapshot_after_refresh(tmp_path: Path) -> None:
    ex = tmp_path / "01-invoice"
    root = ex / ".nlp2dsl"
    reg = ensure_layout(root)
    reg.write_text(
        "environment[name=\"01-invoice\"] {}\ndata {}\nconversation { autofill: true; }\n",
        encoding="utf-8",
    )
    refresh_doql_registry(
        reg,
        intent="send_invoice",
        entities={"amount": 1500, "to": "a@b.pl"},
        phase="ready",
    )
    snap = write_turn_snapshot(
        root,
        turn=1,
        phase="ready",
        response={"status": "ready", "conversation_id": "abc"},
        registry_path=reg,
        run_id="test-run",
    )
    assert snap.is_file()
    assert "registry_observation" in snap.read_text(encoding="utf-8")
