"""Tests for conversation TestTOON structural validation."""

from __future__ import annotations

from pathlib import Path

from nlp2dsl_sdk.conversation_testql import validate_conversation_scenario


def test_validate_hand_authored_conversation() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "05-conversation-flow"
        / ".nlp2dsl"
        / "conversation.testql.toon.yaml"
    )
    if not path.is_file():
        return
    result = validate_conversation_scenario(path)
    assert result.passed, result.summary
    assert "chatstart" in result.endpoints
