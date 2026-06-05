"""Intent pipeline facade."""

from __future__ import annotations

from pact_ir import IntentIR

from nlp2cmd_intent.keywords import KeywordIntentDetector
from nlp2cmd_intent.normalize import QueryNormalizer
from nlp2cmd_intent.nlp2cmd_convert import detection_to_intent_ir
from nlp2cmd_intent.protocols import EntityExtractor, IntentDetector


class PassthroughEntityExtractor:
    def extract(self, query: str):
        from pact_ir import EntityBag

        return EntityBag(values={"raw_query": query})


class KeywordIntentAdapter:
    """Wrap KeywordIntentDetector to satisfy IntentDetector protocol."""

    def __init__(self, detector: KeywordIntentDetector | None = None):
        self._detector = detector or KeywordIntentDetector()

    def detect(self, query: str, *, entities=None) -> IntentIR:
        del entities
        text = query.text if hasattr(query, "text") else str(query)
        return detection_to_intent_ir(self._detector.detect(text), query=text)


def default_intent_detector() -> IntentDetector:
    return KeywordIntentAdapter()


class IntentPipeline:
    """normalize → entities → intent."""

    def __init__(
        self,
        *,
        normalizer: QueryNormalizer | None = None,
        entity_extractor: EntityExtractor | None = None,
        intent_detector: IntentDetector | None = None,
    ):
        self.normalizer = normalizer or QueryNormalizer()
        self.entity_extractor = entity_extractor or PassthroughEntityExtractor()
        self.intent_detector = intent_detector or default_intent_detector()

    def run(self, query: str) -> IntentIR:
        normalized = self.normalizer.normalize(query)
        text = normalized if isinstance(normalized, str) else getattr(normalized, "text", str(query))
        entities = self.entity_extractor.extract(text)
        return self.intent_detector.detect(text, entities=entities)
