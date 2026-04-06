# Migration Guide: In-Memory → Redis + Postgres

Przewodnik krok po kroku migracji z tymczasowego przechowywania w pamięci do trwałej persystencji.

## Przegląd

```
PRZED (in-memory):                    PO (persistent):
─────────────────                     ────────────────
orchestrator.py                       orchestrator.py
  _conversations: dict = {}    →        _store = get_conversation_store()
                                        await _store.get(id) / _store.save(id, state)

workflow.py                           workflow.py
  _history: dict = {}          →        _repo = create_workflow_repo()
                                        await _repo.save_run(...) / _repo.get_run(id)
```

## Wymagania

### nlp-service/requirements.txt
```
redis[hiredis]>=5.0
```

### backend/requirements.txt
```
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29.0
```

## Zmienne środowiskowe

### docker-compose.yml — nlp-service
```yaml
environment:
  - REDIS_URL=redis://redis:6379/0
  - CONVERSATION_TTL=3600    # TTL konwersacji w sekundach (domyślnie 1h)
depends_on:
  - redis
```

### docker-compose.yml — backend
```yaml
environment:
  - POSTGRES_URL=postgresql://app:app@postgres:5432/automation
```

Bez tych zmiennych serwisy używają in-memory fallback — dotychczasowe zachowanie.

---

## Nowe moduły

### nlp-service/app/store/

| Plik | Rola |
|------|------|
| `__init__.py` | `ConversationStore` ABC — interfejs abstrakcyjny |
| `memory.py` | `MemoryConversationStore` — dotychczasowe zachowanie za interfejsem |
| `redis_store.py` | `RedisConversationStore` — sliding TTL, ZSET index, JSON serialization |
| `factory.py` | Singleton factory: `REDIS_URL` → Redis, brak → Memory |

### backend/app/db/

| Plik | Rola |
|------|------|
| `__init__.py` | `WorkflowRepo` ABC + `create_workflow_repo()` factory |
| `memory.py` | `MemoryWorkflowRepo` — backward-compatible fallback |
| `postgres.py` | `PostgresWorkflowRepo` — SQLAlchemy async + auto-create tables |

---

## Zmiany w istniejącym kodzie

### nlp-service/app/orchestrator.py — 4 zmiany

#### Zmiana 1: Import i inicjalizacja store (linie 31–37)

```python
# BYŁO:
# ── In-memory conversation store (MVP) ────
_conversations: dict[str, ConversationState] = {}

# JEST:
from .store.factory import get_conversation_store

_store = get_conversation_store()
```

#### Zmiana 2: start_conversation — async + store.save (linie 72–79)

```python
# BYŁO:
def start_conversation(text: str) -> ConversationResponse:
    state = ConversationState(id=uuid4().hex[:12])
    state.history.append({"role": "user", "text": text})
    _conversations[state.id] = state
    return _process_message(state, text)

# JEST:
async def start_conversation(text: str) -> ConversationResponse:
    state = ConversationState(id=uuid4().hex[:12])
    state.history.append({"role": "user", "text": text})
    result = _process_message(state, text)
    await _store.save(state.id, state.model_dump())
    return result
```

#### Zmiana 3: continue_conversation — async + store.get/save (linie 82–99)

```python
# BYŁO:
def continue_conversation(conversation_id: str, text: str) -> ConversationResponse:
    state = _conversations.get(conversation_id)
    if not state:
        state = ConversationState(id=conversation_id)
        _conversations[conversation_id] = state
    state.history.append({"role": "user", "text": text})
    return _process_message(state, text)

# JEST:
async def continue_conversation(conversation_id: str, text: str) -> ConversationResponse:
    raw = await _store.get(conversation_id)
    if not raw:
        state = ConversationState(id=conversation_id)
    else:
        state = ConversationState(**raw)
    state.history.append({"role": "user", "text": text})
    result = _process_message(state, text)
    await _store.save(state.id, state.model_dump())
    return result
```

#### Zmiana 4: get_conversation — async + store.get (linie 102–107)

```python
# BYŁO:
def get_conversation(conversation_id: str) -> ConversationState | None:
    return _conversations.get(conversation_id)

# JEST:
async def get_conversation(conversation_id: str) -> ConversationState | None:
    raw = await _store.get(conversation_id)
    if raw:
        return ConversationState(**raw)
    return None
```

---

### nlp-service/app/main.py — 6 zmian

Wszystkie wywołania funkcji orchestratora wymagają `await`:

```python
# /chat/start
return await start_conversation(text)

# /chat/message
return await continue_conversation(conversation_id, text)

# /chat/{id}
state = await get_conversation(conversation_id)

# WebSocket — streaming STT
response = await continue_conversation(conversation_id, transcript)

# WebSocket — batch STT fallback
response = await continue_conversation(conversation_id, transcript)
```

Endpoint `/health` rozszerzony o dane store:

```python
@app.get("/health")
async def health():
    store = get_conversation_store()
    return {
        "status": "ok",
        "conversation_store": type(store).__name__,
        "active_conversations": await store.count(),
        ...
    }
```

---

### backend/app/workflow.py — 3 zmiany

#### Zmiana 1: Import i inicjalizacja repo

```python
# BYŁO:
_history: dict[str, WorkflowResult] = {}

# JEST:
from .db import create_workflow_repo

_repo = create_workflow_repo()
```

#### Zmiana 2: run_workflow — save_run zamiast dict assignment

```python
# BYŁO (dwa miejsca):
_history[workflow_id] = result

# JEST (dwa miejsca — sukces i fail-fast):
await _repo.save_run(
    workflow_id=workflow_id,
    name=req.name,
    status=result.status.value,
    data={
        "trigger": req.trigger or "manual",
        "steps": [s.model_dump() for s in result.steps],
    },
)
```

#### Zmiana 3: get_history i get_workflow — repo zamiast dict

```python
# BYŁO:
@router.get("/history", response_model=list[WorkflowResult])
async def get_history():
    return list(_history.values())

@router.get("/history/{workflow_id}", response_model=WorkflowResult)
async def get_workflow(workflow_id: str):
    wf = _history.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

# JEST:
@router.get("/history")
async def get_history():
    return await _repo.list_runs()

@router.get("/history/{workflow_id}")
async def get_workflow(workflow_id: str):
    run = await _repo.get_run(workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return run
```

---

## Schemat danych

### Redis (nlp-service)

```
conv:{conversation_id}   STRING (JSON)   TTL=3600s
conv:index               ZSET            score=timestamp, member=conversation_id
```

Przykład zawartości klucza `conv:abc123`:
```json
{
  "id": "abc123",
  "intent": "send_invoice",
  "entities": {"amount": 1500, "currency": "PLN", "to": "klient@firma.pl"},
  "missing": [],
  "status": "ready",
  "history": [
    {"role": "user", "text": "Wyślij fakturę na 1500 PLN do klient@firma.pl"},
    {"role": "assistant", "text": "Workflow gotowy: send_invoice (1 kroków). Wyślij 'uruchom' aby wykonać."}
  ]
}
```

### Postgres (backend)

Tworzy się automatycznie przez SQLAlchemy `create_all` przy pierwszym użyciu. Ręczne SQL:

```sql
CREATE TABLE IF NOT EXISTS workflow_runs (
    id          VARCHAR(32) PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    status      VARCHAR(32) NOT NULL,
    trigger     VARCHAR(32) DEFAULT 'manual',
    steps       JSONB DEFAULT '[]'::jsonb,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workflow_runs_name    ON workflow_runs(name);
CREATE INDEX idx_workflow_runs_status  ON workflow_runs(status);
CREATE INDEX idx_workflow_runs_created ON workflow_runs(created_at DESC);
```

---

## Weryfikacja

### Test 1: Konwersacja przeżywa restart (Redis)

```bash
# Stwórz konwersację
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl"}'
# Zapamiętaj conversation_id z odpowiedzi

# Restart nlp-service
docker compose restart nlp-service

# Kontynuuj — powinno działać
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "TWOJE_ID", "text": "uruchom"}'
# ✅ Stan odczytany z Redis
```

### Test 2: Historia workflow przeżywa restart (Postgres)

```bash
# Uruchom workflow
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "steps": [{"action": "send_invoice", "config": {"amount": 100, "to": "a@b.com"}}]}'

# Restart backend
docker compose restart backend

# Sprawdź historię
curl http://localhost:8010/workflow/history
# ✅ Workflow widoczny po restarcie
```

### Test 3: Health check — typ store

```bash
curl http://localhost:8002/health
# Z REDIS_URL:    "conversation_store": "RedisConversationStore"
# Bez REDIS_URL:  "conversation_store": "MemoryConversationStore"
```

### Test 4: Fallback do memory (bez Redis)

```bash
# Usuń REDIS_URL z docker-compose.yml lub uruchom lokalnie bez env
uvicorn app.main:app --port 8002

curl http://localhost:8002/health
# "conversation_store": "MemoryConversationStore" ← automatyczny fallback
```
