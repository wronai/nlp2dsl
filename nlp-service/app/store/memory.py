"""
MemoryConversationStore — in-memory fallback (zachowanie dotychczasowe).
"""

from app.store import ConversationStore


class MemoryConversationStore(ConversationStore):

    def __init__(self):
        self._data: dict[str, dict] = {}

    async def get(self, conversation_id: str) -> dict | None:
        return self._data.get(conversation_id)

    async def save(self, conversation_id: str, state: dict) -> None:
        self._data[conversation_id] = state

    async def delete(self, conversation_id: str) -> None:
        self._data.pop(conversation_id, None)

    async def count(self) -> int:
        return len(self._data)
