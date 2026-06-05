"""UTF-8 stdio for nlp2dsl-show CLI — delegates to nlp2dsl_sdk when available."""

from __future__ import annotations

try:
    from nlp2dsl_sdk.encoding import configure_utf8 as configure_utf8
except ImportError:
    import locale
    import os
    import sys

    def configure_utf8(*, force: bool = False) -> None:
        if not force and os.environ.get("NLP2DSL_UTF8", "1").strip().lower() in {
            "0",
            "false",
            "no",
            "off",
        }:
            return
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")
        explicit_utf8 = any(
            "utf" in (os.environ.get(key) or "").lower()
            for key in ("LC_ALL", "LANG", "LC_CTYPE")
        )
        if not explicit_utf8:
            os.environ["LANG"] = "C.UTF-8"
            os.environ["LC_ALL"] = "C.UTF-8"
            os.environ["LC_CTYPE"] = "C.UTF-8"
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                try:
                    reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        for loc in ("C.UTF-8", "en_US.UTF-8"):
            try:
                locale.setlocale(locale.LC_ALL, loc)
                break
            except locale.Error:
                continue

    configure_utf8()
