"""Tests for process.paths glob validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.conversation.doql_context import DoqlProcessPolicy, DoqlTaskContext
from app.validation.path_policy import (
    example_relative_path,
    path_allowed_by_patterns,
    path_matches_glob,
    validate_process_path,
)


def test_path_matches_glob_fixtures() -> None:
    assert path_matches_glob("fixtures/faktura.pdf", "fixtures/**")
    assert path_matches_glob("fixtures/sub/x.pdf", "fixtures/**")
    assert not path_matches_glob("other/x.pdf", "fixtures/**")


def test_path_allowed_by_patterns_empty_means_allow() -> None:
    assert path_allowed_by_patterns("any/path", [])


def test_validate_process_path_denies_outside_scope(tmp_path: Path, monkeypatch) -> None:
    ex = tmp_path / "01-invoice"
    fixtures = ex / "fixtures"
    fixtures.mkdir(parents=True)
    pdf = fixtures / "faktura.pdf"
    pdf.write_text("FAKTURA", encoding="utf-8")
    outside = ex / "secret" / "x.pdf"
    outside.parent.mkdir(parents=True)
    outside.write_text("x", encoding="utf-8")

    monkeypatch.setenv("NLP2DSL_EXAMPLE_DIR", str(ex))
    ctx = DoqlTaskContext(process=DoqlProcessPolicy(paths_read=["fixtures/**"]))

    ok = validate_process_path(ctx, str(pdf), access="read")
    assert ok is None

    denied = validate_process_path(ctx, str(outside), access="read")
    assert denied is not None
    assert "process.paths.read" in denied


def test_example_relative_path(tmp_path: Path) -> None:
    ex = tmp_path / "example"
    ex.mkdir()
    child = ex / "fixtures" / "a.pdf"
    child.parent.mkdir(parents=True)
    child.touch()
    rel = example_relative_path(child, ex)
    assert rel == "fixtures/a.pdf"
