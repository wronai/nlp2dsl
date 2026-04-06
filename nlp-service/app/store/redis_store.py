"""
RedisConversationStore — persystencja stanu konwersacji w Redis.

Schemat kluczy:
  conv:{conversation_id}  STRING (JSON)  TTL=default_ttl
  conv:index              ZSET (score=timestamp, member=conversation_id)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import redis.asyncio as aioredis

from . import ConversationStore

log = logging.getLogger("store.redis")


class RedisConversationStore(ConversationStore):

    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self._redis: aioredis.Redis = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._ttl = default_ttl
        self._prefix = "conv:"
        self._index_key = "conv:index"

    def _key(self, conversation_id: str) -> str:
        return f"{self._prefix}{conversation_id}"

    async def get(self, conversation_id: str) -> Optional[dict]:
        raw = await self._redis.get(self._key(conversation_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Corrupt conversation data for %s", conversation_id)
            return None

    async def save(self, conversation_id: str, state: dict) -> None:
        payload = json.dumps(state, default=str)
        await self._redis.set(self._key(conversation_id), payload, ex=self._ttl)
        await self._redis.zadd(self._index_key, {conversation_id: time.time()})

    async def delete(self, conversation_id: str) -> None:
        await self._redis.delete(self._key(conversation_id))
        await self._redis.zrem(self._index_key, conversation_id)

    async def count(self) -> int:
        return await self._redis.zcard(self._index_key)

    async def close(self) -> None:
        await self._redis.aclose()
