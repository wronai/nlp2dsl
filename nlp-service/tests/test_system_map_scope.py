"""Tests for DOQL-scoped action registry (C1)."""

from __future__ import annotations

import pytest

from app.conversation.doql_context import DoqlCommand, DoqlTaskContext
from app.conversation.system_map import (
    command_meta,
    known_action_names,
    scoped_action_registry,
    set_doql_context,
)
from app.registry import ACTIONS_REGISTRY, get_required_fields


@pytest.fixture(autouse=True)
def _reset_doql_context() -> None:
    set_doql_context(None)
    yield
    set_doql_context(None)


def test_known_action_names_without_doql() -> None:
    set_doql_context(None)
    names = known_action_names()
    assert "send_invoice" in names
    assert len(names) == len(ACTIONS_REGISTRY)


def test_known_action_names_doql_subset() -> None:
    ctx = DoqlTaskContext(
        example_name="test",
        commands=[
            DoqlCommand(name="send_email", required=["to"], optional=["subject", "body"]),
        ],
    )
    set_doql_context(ctx)
    names = known_action_names()
    assert names == {"send_email"}
    assert get_required_fields("send_email") == ["to"]
    assert get_required_fields("send_invoice") == []


def test_scoped_action_registry() -> None:
    ctx = DoqlTaskContext(
        example_name="test",
        commands=[DoqlCommand(name="send_invoice", required=["amount", "to"], description="Invoice")],
    )
    set_doql_context(ctx)
    scoped = scoped_action_registry()
    assert list(scoped.keys()) == ["send_invoice"]
    assert scoped["send_invoice"]["required"] == ["amount", "to"]
    meta = command_meta("send_invoice")
    assert meta["description"] == "Invoice"
