"""
Store factory — wybiera backend na podstawie env vars.

  REDIS_URL set   → RedisConversationStore
  REDIS_URL unset → MemoryConversationStore

Użycie:
  from app.store.factory import get_conversation_store
  store = get_conversation_store()
"""

import logging

from app.store import ConversationStore
from app.store.memory import MemoryConversationStore

log = logging.getLogger("store.factory")

_instance: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Singleton factory — zwraca store odpowiedni dla środowiska."""
    global _instance
    if _instance is not None:
        return _instance

    from app.config import NLPServiceSettings

    settings = NLPServiceSettings(_env_file=None)
    redis_url = settings.redis_url
    conv_ttl = settings.conversation_ttl

    if redis_url:
        try:
            from app.store.redis_store import RedisConversationStore
            _instance = RedisConversationStore(redis_url=redis_url, default_ttl=conv_ttl)
            log.info("Using RedisConversationStore (TTL=%ds)", conv_ttl)
        except Exception as e:
            log.warning("Redis unavailable (%s), falling back to memory store", e)
            _instance = MemoryConversationStore()
    else:
        _instance = MemoryConversationStore()
        log.info("Using MemoryConversationStore (set REDIS_URL for persistence)")

    return _instance
