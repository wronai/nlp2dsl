# testql-conversations

Structural validation of conversation **TestTOON** scenarios and persistence of conversation trace artifacts.

## Usage

```python
from pathlib import Path
from testql_conversations import (
    validate_conversation_scenario,
    write_conversation_artifacts,
    format_transcript,
)

result = validate_conversation_scenario("scenarios/send-invoice.testql.toon.yaml")
assert result.passed, result.summary

write_conversation_artifacts(
    ".nlp2dsl",
    trace={"conversation_id": "…", "turns": [...]},
)
# → conversation.trace.json/yaml, conversation.transcript.md
```

Optional dependency: `testql` (for full TestTOON parse; falls back to text scan).

Used by **koru** (`validate_testql_conversations.py`). Shims: `nlp2dsl_sdk.conversation_testql`, `conversation_artifacts`.
