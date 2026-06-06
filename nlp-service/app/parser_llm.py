"""Backward-compat shim — use app.routing.parser.llm."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import NLPResult

__all__ = ["LLM_MODEL", "_detect_provider", "parse_llm"]

_LLM_EXPORTS: dict[str, Any] | None = None


def _llm_module():
    global _LLM_EXPORTS
    if _LLM_EXPORTS is None:
        from app.routing.parser import llm as mod

        _LLM_EXPORTS = {
            "LLM_MODEL": mod.LLM_MODEL,
            "_detect_provider": mod._detect_provider,
            "parse_llm": mod.parse_llm,
        }
    return _LLM_EXPORTS


def __getattr__(name: str) -> Any:
    exports = _llm_module()
    if name in exports:
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
