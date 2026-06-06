"""
Keyword patterns for intent detection.

This module contains pattern definitions and loading functionality
for the keyword-based intent detection system.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import nlp2cmd_intent.keywords as _keywords_pkg
from nlp2cmd_intent.data_files import bundled_data_file, find_data_files as _find_data_files_default
from nlp2cmd_intent.keywords.pattern_loaders import (
    clean_string_list,
    merge_patterns_payload,
    parse_domain_boosters,
    parse_explicit_overrides,
    parse_fast_path_settings,
    parse_priority_intents,
    read_json_object,
)

logger = logging.getLogger(__name__)


def _find_data_files(**kwargs):
    """Indirection so tests can monkeypatch nlp2cmd.generation.keywords.find_data_files."""
    fn = getattr(_keywords_pkg, "find_data_files", _find_data_files_default)
    return fn(**kwargs)


def _normalize_polish_text(text: str) -> str:
    """Normalize Polish text for pattern matching."""
    return text.lower().strip()


def _dedupe_case_insensitive(items: List[str]) -> List[str]:
    """Deduplicate items case-insensitively while preserving order."""
    seen = set()
    out = []
    for item in items:
        lowered = item.lower()
        if lowered not in seen:
            seen.add(lowered)
            out.append(item)
    return out


class KeywordPatterns:
    """Manages keyword patterns for intent detection."""

    def __init__(self, custom_patterns_file: Optional[str] = None):
        self.patterns: Dict[str, Dict[str, List[str]]] = {}
        self.domain_boosters: Dict[str, List[str]] = {}
        self.priority_intents: Dict[str, List[str]] = {}
        self.fast_path_browser_keywords: List[str] = []
        self.fast_path_search_keywords: List[str] = []
        self.fast_path_common_images: set[str] = set()
        self.explicit_overrides: List[Tuple[str, str, str, str]] = []

        self._load_patterns_from_json(custom_patterns_file)
        self._load_detector_config_from_json()
        self._load_fast_path_overrides_from_json()

        strict = os.environ.get("NLP2CMD_STRICT_CONFIG", "").strip().lower() in {"1", "true", "yes"}
        if strict and not self.patterns:
            raise FileNotFoundError(
                "NLP2CMD_STRICT_CONFIG is set but no patterns data files were found. "
                "Set NLP2CMD_PATTERNS_FILE or ensure data/patterns.json is accessible."
            )

    def _pattern_files(self, custom_patterns_file: Optional[str]) -> list[Path]:
        files: list[Path] = []
        if custom_patterns_file:
            files.append(Path(custom_patterns_file))
        files.extend(
            _find_data_files(
                explicit_path=os.environ.get("NLP2CMD_PATTERNS_FILE"),
                default_filename="patterns.json",
            )
        )
        return files

    def _load_patterns_from_json(self, custom_patterns_file: Optional[str] = None) -> None:
        """Load patterns from external JSON file."""
        base: Dict[str, Dict[str, List[str]]] = {}
        for pattern_file in self._pattern_files(custom_patterns_file):
            payload = read_json_object(pattern_file)
            if payload is None:
                continue
            merge_patterns_payload(
                base,
                payload,
                normalizer=_normalize_polish_text,
                dedupe=_dedupe_case_insensitive,
            )
            logger.debug("Loaded patterns from %s", pattern_file)
        self.patterns = base

    def _apply_detector_config(self, payload: dict) -> None:
        self.domain_boosters.update(
            parse_domain_boosters(payload, normalizer=_normalize_polish_text)
        )
        self.priority_intents.update(
            parse_priority_intents(payload, normalizer=_normalize_polish_text)
        )
        browser, search, images = parse_fast_path_settings(
            payload,
            normalizer=_normalize_polish_text,
            dedupe=_dedupe_case_insensitive,
        )
        if browser:
            self.fast_path_browser_keywords = browser
        if search:
            self.fast_path_search_keywords = search
        if images:
            self.fast_path_common_images = images

    def _load_detector_config_from_json(self) -> None:
        """Load detector configuration from JSON files."""
        for path in _find_data_files(
            explicit_path=os.environ.get("NLP2CMD_DETECTOR_CONFIG_FILE"),
            default_filename="detector_config.json",
            alt_filenames=("keyword_intent_detector_config.json",),
        ):
            payload = read_json_object(path)
            if payload is None:
                continue
            self._apply_detector_config(payload)
            logger.debug("Loaded detector config from %s", path)

    def _load_fast_path_overrides_from_json(self) -> None:
        """Load high-priority substring overrides for fast-path detection."""
        bundled = bundled_data_file("fast_path_overrides.json")
        if bundled is not None:
            payload = read_json_object(bundled)
            if payload is not None:
                loaded = parse_explicit_overrides(payload)
                if loaded:
                    self.explicit_overrides = loaded
                    logger.debug("Loaded %d bundled fast-path overrides", len(loaded))

        for path in _find_data_files(
            explicit_path=os.environ.get("NLP2CMD_FAST_PATH_OVERRIDES_FILE"),
            default_filename="fast_path_overrides.json",
        ):
            if bundled is not None and path == bundled:
                continue
            payload = read_json_object(path)
            if payload is None:
                continue
            loaded = parse_explicit_overrides(payload)
            if loaded:
                self.explicit_overrides = loaded
                logger.debug("Loaded %d fast-path overrides from %s", len(loaded), path)
                return

    def get_domain_patterns(self, domain: str) -> Dict[str, List[str]]:
        return self.patterns.get(domain, {})

    def get_intent_patterns(self, domain: str, intent: str) -> List[str]:
        return self.patterns.get(domain, {}).get(intent, [])

    def has_domain(self, domain: str) -> bool:
        return domain in self.patterns

    def has_intent(self, domain: str, intent: str) -> bool:
        return intent in self.patterns.get(domain, {})

    def list_domains(self) -> List[str]:
        return list(self.patterns.keys())

    def list_intents(self, domain: str) -> List[str]:
        return list(self.patterns.get(domain, {}).keys())

    def add_pattern(self, domain: str, intent: str, keywords: List[str]) -> None:
        if domain not in self.patterns:
            self.patterns[domain] = {}
        clean = clean_string_list(keywords, normalizer=_normalize_polish_text)
        if clean:
            existing = self.patterns[domain].get(intent, [])
            self.patterns[domain][intent] = _dedupe_case_insensitive([*clean, *existing])

    def get_domain_boosters(self, domain: str) -> List[str]:
        return self.domain_boosters.get(domain, [])

    def get_priority_intents(self, domain: str) -> List[str]:
        return self.priority_intents.get(domain, [])
