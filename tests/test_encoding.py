"""Tests for UTF-8 stdio configuration."""

import io
import os
import sys

from nlp2dsl_sdk.encoding import configure_utf8, utf8_auto_enabled


def test_configure_utf8_reconfigures_stdout(monkeypatch):
    buf = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stdout", buf)
    configure_utf8(force=True)
    assert sys.stdout.encoding.lower().replace("-", "") == "utf8"


def test_configure_utf8_respects_disable(monkeypatch):
    monkeypatch.setenv("NLP2DSL_UTF8", "0")
    buf = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stdout", buf)
    configure_utf8()
    assert sys.stdout.encoding.lower() == "ascii"


def test_configure_utf8_upgrades_ascii_locale(monkeypatch):
    monkeypatch.delenv("NLP2DSL_UTF8", raising=False)
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("LC_ALL", "C")
    configure_utf8(force=True)
    assert "UTF-8" in os.environ["LANG"]
    assert os.environ["PYTHONIOENCODING"] == "utf-8"


def test_utf8_auto_enabled_default(monkeypatch):
    monkeypatch.delenv("NLP2DSL_UTF8", raising=False)
    assert utf8_auto_enabled() is True
    monkeypatch.setenv("NLP2DSL_UTF8", "0")
    assert utf8_auto_enabled() is False
