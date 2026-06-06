"""UTF-8 stdio setup — fixes broken Polish output (znajdź → znajd?) on ASCII locales."""

from __future__ import annotations

import locale
import os
import sys

# Only widely-available locales (pl_PL.UTF-8 often missing → setlocale warnings in bash)
_UTF8_LOCALES = ("C.UTF-8", "en_US.UTF-8")
_DISABLE_VALUES = frozenset({"0", "false", "no", "off"})
_AUTO_CONFIGURED = False


def utf8_auto_enabled() -> bool:
    """Whether automatic UTF-8 setup is enabled (default: on)."""
    return os.environ.get("NLP2DSL_UTF8", "1").strip().lower() not in _DISABLE_VALUES


def _explicit_utf8_locale() -> bool:
    """True only when the effective character locale is UTF-8."""
    for key in ("LC_ALL", "LC_CTYPE", "LANG"):
        value = os.environ.get(key)
        if not value:
            continue
        return "utf" in value.lower()
    return False


def _apply_utf8_locale_env() -> None:
    """Set PYTHONUTF8 env; upgrade C/POSIX/empty locale to C.UTF-8."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    if _explicit_utf8_locale():
        return

    os.environ["LANG"] = "C.UTF-8"
    os.environ["LC_ALL"] = "C.UTF-8"
    os.environ["LC_CTYPE"] = "C.UTF-8"


def _reconfigure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _set_utf8_locale() -> None:
    for loc in _UTF8_LOCALES:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return
        except locale.Error:
            continue


def configure_utf8(*, force: bool = False) -> None:
    """
    Reconfigure stdio to UTF-8 and prefer a UTF-8 locale.

    Called automatically on ``import nlp2dsl_sdk`` (and when this module loads).
    Disable with ``NLP2DSL_UTF8=0``.
    """
    if not force and not utf8_auto_enabled():
        return

    _apply_utf8_locale_env()
    _reconfigure_stdio()
    _set_utf8_locale()


def _auto_configure_once() -> None:
    global _AUTO_CONFIGURED
    if _AUTO_CONFIGURED:
        return
    _AUTO_CONFIGURED = True
    configure_utf8()


def utf8_open(path, mode="r", **kwargs):
    """open() with UTF-8 default encoding."""
    if "encoding" not in kwargs and "b" not in mode:
        kwargs["encoding"] = "utf-8"
    return open(path, mode, **kwargs)


if utf8_auto_enabled():
    _auto_configure_once()
