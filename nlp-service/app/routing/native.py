"""Natywne trasy z nlp2dsl.yaml — przed parserem rules/LLM."""

from __future__ import annotations

import re
from typing import Any

from app.governance.config import get_access_config


def _match_route(text: str, route: dict[str, Any]) -> bool:
    text_lower = text.lower().strip()
    return _patterns_match(text_lower, route.get("patterns") or []) or _aliases_match(
        text_lower,
        route.get("aliases") or [],
    )


def _patterns_match(text_lower: str, patterns: list[Any]) -> bool:
    return any(
        _pattern_matches(text_lower, pattern)
        for pattern in patterns
        if isinstance(pattern, dict)
    )


def _pattern_matches(text_lower: str, pattern: dict[str, Any]) -> bool:
    ptype = (pattern.get("type") or "substring").lower()
    if ptype == "regex":
        return _regex_pattern_matches(text_lower, pattern)
    if ptype == "keywords":
        return _keywords_pattern_matches(text_lower, pattern)
    return _substring_pattern_matches(text_lower, pattern)


def _regex_pattern_matches(text_lower: str, pattern: dict[str, Any]) -> bool:
    rx = pattern.get("value") or pattern.get("pattern") or ""
    return bool(rx and re.search(rx, text_lower, re.IGNORECASE))


def _keywords_pattern_matches(text_lower: str, pattern: dict[str, Any]) -> bool:
    keywords = pattern.get("keywords") or []
    return bool(keywords) and all(str(kw).lower() in text_lower for kw in keywords)


def _substring_pattern_matches(text_lower: str, pattern: dict[str, Any]) -> bool:
    substring = pattern.get("value") or pattern.get("substring") or ""
    return bool(substring and str(substring).lower() in text_lower)


def _aliases_match(text_lower: str, aliases: list[Any]) -> bool:
    return any(str(alias).lower() in text_lower for alias in aliases)


def resolve_native_intent(text: str) -> dict[str, Any] | None:
    """
    Zwraca {action, resource_area?, permission_action?, uri?} lub None.
    """
    if not (text or "").strip():
        return None
    cfg = get_access_config()
    action_areas = cfg.action_to_area()

    native_hit = _resolve_configured_route(text, cfg.native_routes, action_areas)
    if native_hit:
        return native_hit

    # Domyślna trasa: akcje z YAML resource_areas (aliasy w actions, DOQL scope)
    from app.conversation.system_map import scoped_action_registry

    return _resolve_action_alias(text, scoped_action_registry())


def _resolve_configured_route(
    text: str,
    routes: list[dict[str, Any]],
    action_areas: dict[str, str],
) -> dict[str, Any] | None:
    for route in routes:
        action = route.get("action") or route.get("intent")
        if not action or not _match_route(text, route):
            continue
        return _route_decision(str(action), route, action_areas)
    return None


def _route_decision(
    action: str,
    route: dict[str, Any],
    action_areas: dict[str, str],
) -> dict[str, Any]:
    return {
        "action": action,
        "resource_area": route.get("resource_area") or action_areas.get(action),
        "permission_action": route.get("permission_action", "execute"),
        "uri": route.get("uri"),
        "source": "native_routing",
    }


def _resolve_action_alias(
    text: str,
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    text_lower = text.lower()
    best = _best_action_alias(text_lower, registry)
    if not best:
        return None
    action_name = best[0]
    meta = registry.get(action_name, {})
    return {
        "action": action_name,
        "resource_area": meta.get("resource_area"),
        "permission_action": meta.get("permission_action", "execute"),
        "uri": meta.get("resource_uri"),
        "source": "action_aliases",
    }


def _best_action_alias(
    text_lower: str,
    registry: dict[str, dict[str, Any]],
) -> tuple[str, int] | None:
    best: tuple[str, int] | None = None
    for action_name, meta in registry.items():
        if meta.get("native_route") is False:
            continue
        best = _best_alias_for_action(text_lower, action_name, meta, best)
    return best


def _best_alias_for_action(
    text_lower: str,
    action_name: str,
    meta: dict[str, Any],
    current: tuple[str, int] | None,
) -> tuple[str, int] | None:
    best = current
    for alias in meta.get("aliases") or []:
        alias_text = str(alias).lower()
        if alias_text in text_lower and (best is None or len(alias_text) > best[1]):
            best = (action_name, len(alias_text))
    return best
