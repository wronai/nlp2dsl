"""Tests for conversation TestTOON structural validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from nlp2dsl_sdk.conversation_testql import (
    _endpoints_from_text,
    validate_conversation_scenario,
)


def test_endpoints_from_text_scans_nlp_dsl_rows() -> None:
    text = """
TYPE: conversation
NLP_DSL[1]{endpoint, payload}:
  chatstart, {"text": "hello"}
NLP_DSL[1]{endpoint, payload}:
  chatmessage, {"conversationId": "x", "text": "uruchom"}
"""
    assert _endpoints_from_text(text) == ["chatstart", "chatmessage"]


def test_validate_hand_authored_conversation() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "05-conversation-flow"
        / ".nlp2dsl"
        / "conversation.testql.toon.yaml"
    )
    if not path.is_file():
        pytest.skip("conversation.testql.toon.yaml not present")
    pytest.importorskip("testql")
    result = validate_conversation_scenario(path)
    assert result.passed, result.summary
    assert "chatstart" in result.endpoints
