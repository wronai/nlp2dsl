"""NL → IntentIR pipeline."""

from nlp2cmd_intent.clarification import (
    IntentClarificationRequired,
    clarification_enforced,
    ensure_intent_clear,
)
from nlp2cmd_intent.facade import IntentPipeline, default_intent_detector
from nlp2cmd_intent.input import analyze_query
from nlp2cmd_intent.keywords import DetectionResult, KeywordIntentDetector, KeywordPatterns
from nlp2cmd_intent.normalize import QueryNormalizer
from nlp2cmd_intent.nlp2cmd_convert import detection_to_intent_ir
from nlp2cmd_intent.protocols import EntityExtractor, IntentDetector

__all__ = [
    "DetectionResult",
    "EntityExtractor",
    "IntentClarificationRequired",
    "IntentDetector",
    "IntentPipeline",
    "KeywordIntentDetector",
    "KeywordPatterns",
    "QueryNormalizer",
    "analyze_query",
    "clarification_enforced",
    "default_intent_detector",
    "detection_to_intent_ir",
    "ensure_intent_clear",
]

__version__ = "0.0.28"
