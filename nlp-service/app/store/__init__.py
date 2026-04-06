"""
Conversation store — abstrakcja persystencji stanu rozmów.

Factory function `get_conversation_store()` zwraca odpowiednią
implementację na podstawie env REDIS_URL:
  - set    → RedisConversationStore
  - unset  → MemoryConversationStore (fallback)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class ConversationStore(ABC):
    """Abstrakcja persystencji stanu konwersacji."""

    @abstractmethod
    async def get(self, conversation_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def save(self, conversation_id: str, state: dict) -> None:
        ...

    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...
