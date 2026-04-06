# Obsługa Brakującej Konfiguracji w NLP2DSL

Dokumentacja opisująca zachowanie systemu, gdy brakuje kluczowych danych konfiguracyjnych.

## 🔍 Scenariusze Brakującej Konfiguracji

### 1. Brak kluczy API LLM

#### Zachowanie systemu:
```python
# Funkcja _detect_provider() w parser_llm.py
def _detect_provider() -> str:
    """Detect which LLM provider is configured."""
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    # ... inne providery
    return "none"  # Gdy brak kluczy API
```

#### Tryb "auto" (domyślny):
- System używa parsera reguł jako fallback
- Log: `Rules parser sufficient (confidence=0.80)`
- Działa dla prostych komend (faktury, emaile)

#### Tryb "llm" (jawnie określony):
```bash
# Odpowiedź API przy braku klucza
HTTP/1.1 503 Service Unavailable
{
  "detail": "No LLM provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_URL."
}
```

#### Przykład:
```bash
# Bez klucza API, tryb auto (działa)
curl -X POST http://localhost:8010/workflow/from-text \
  -d '{"text": "Wyślij fakturę na 150 PLN"}'
# ✅ Odpowiedź: status=complete (parser reguł)

# Bez klucza API, tryb llm (błąd)
curl -X POST http://localhost:8010/workflow/from-text \
  -d '{"text": "Wyślij fakturę", "mode": "llm"}'
# ❌ Odpowiedź: 503 Service Unavailable
```

### 2. Brak połączenia z bazą danych

#### PostgreSQL:
```yaml
# docker-compose.yml
postgres:
  environment:
    POSTGRES_USER: app
    POSTGRES_PASSWORD: app
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U app"]
```

#### Zachowanie:
- Kontener `backend` nie startuje bez zdrowej bazy
- Log: `database "automation" does not exist`
- System nie działa w pełni (brak historii workflow)

#### Obejście:
```bash
# Tymczasowe uruchomienie bez bazy
docker compose up -d redis nlp-service worker
# Backend będzie próbował połączyć się w pętli
```

### 3. Brak Redis (cache/kolejki)

#### Zachowanie:
- System działa bez cache
- Konwersacje przechowywane w pamięci (utrata przy restarcie)
- Brak kolejek dla zadań asynchronicznych

#### Log ostrzeżenia:
```
WARNING: Redis connection failed, using in-memory storage
```

### 4. Brak WORKER_URL

#### Konfiguracja w backend:
```yaml
backend:
  environment:
    - WORKER_URL=http://worker:8000
```

#### Zachowanie:
- Workflow nie może być wykonany
- Błąd: `Connection refused` przy próbie wykonania
- DSL może być generowany, ale execution kończy się błędem

### 5. Brak NLP_SERVICE_URL

#### Zachowanie:
- Backend nie może przetworzyć tekstu
- Błąd: `NLP service unavailable`
- Endpointy `/workflow/from-text` nie działają

## 🛡️ Mechanizmy Fallback

### 1. Parser Reguł vs LLM

```python
# main.py - logika auto mode
if rules_result.intent.confidence >= LLM_FALLBACK_THRESHOLD:
    log.info("Rules parser sufficient (confidence=%.2f)", rules_result.intent.confidence)
    return rules_result  # Użyj reguł

# Spróbuj LLM jeśli dostępny
if provider != "none":
    log.info("Rules confidence too low, trying LLM…")
    # ... wywołanie LLM
```

### 2. Mock Responses w Worker

Worker zawsze zwraca symulowane odpowiedzi, nawet bez prawdziwych integracji:

```python
# worker.py
@action("send_invoice")
async def handle_send_invoice(config: dict) -> dict:
    invoice_id = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {"invoice_id": invoice_id, "sent_to": config.get("to")}
```

### 3. In-Memory Storage

Gdy Redis niedostępny:
```python
# orchestrator.py
_conversations = {}  # In-memory fallback

def get_conversation(conversation_id: str):
    return _conversations.get(conversation_id)
```

## 📋 Tabela Zachowań

| Komponent | Brak konfiguracji | Fallback | Status systemu |
|-----------|-------------------|----------|----------------|
| LLM API | Brak kluczy | Parser reguł | ⚠️ Ograniczony |
| PostgreSQL | Błąd połączenia | - | ❌ Niepełny |
| Redis | Błąd połączenia | In-memory | ⚠️ Ograniczony |
| Worker | Brak URL | - | ❌ Bez execution |
| NLP Service | Brak URL | - | ❌ Bez NLP |
| SMTP | Brak konfiguracji | Mock email | ✅ Działa |
| Slack | Brak webhook | Mock notify | ✅ Działa |

## 🔧 Diagnostyka

### Sprawdzanie statusu:
```bash
# Health check wszystkich serwisów
curl http://localhost:8010/health

# Status LLM
curl http://localhost:8002/health
# Odpowiedź: {"llm_provider": "disabled (rules only)"}

# Lista akcji worker
curl http://localhost:8004/health
```

### Logi do monitorowania:
```bash
# LLM fallback
docker compose logs nlp-service | grep "Rules parser"

# Błędy połączenia
docker compose logs backend | grep "connection"

# Status cache
docker compose logs backend | grep "Redis"
```

## 💡 Rekomendacje

### 1. Konfiguracja minimalna:
```env
# .env.example - minimalne działanie
LLM_MODEL=rules  # Wymuś parser reguł
# Bez kluczy API = tryb offline
```

### 2. Konfiguracja produkcyjna:
```env
# Pełne funkcje
OPENROUTER_API_KEY=sk-or-...
REDIS_URL=redis://localhost:6379/0
WORKER_URL=http://worker:8000
NLP_SERVICE_URL=http://nlp-service:8002
```

### 3. Error handling w kodzie:
```python
try:
    result = await call_llm(text)
except Exception as e:
    log.warning("LLM failed, using rules parser")
    result = parse_rules(text)
```

## 🚨 Najczęstsze Problemy

1. **"Nie rozpoznałem intencji"** - brak LLM + skomplikowany tekst
2. **"Workflow execution failed"** - worker niedostępny
3. **"Conversation not found"** - Redis restart + in-memory storage
4. **"503 Service Unavailable"** - próba użycia LLM bez klucza

## 📝 Przykładowe Scenariusze

### Scenariusz 1: Tylko parser reguł
```bash
# Konfiguracja
cp .env.example .env
# (bez uzupełniania kluczy API)

# Wynik
✅ Proste komendy działają
❌ Złożone komendy nie są rozumiane
```

### Scenariusz 2: Brak bazy danych
```bash
# Konfiguracja
docker compose stop postgres

# Wynik
✅ DSL generowany
✅ Workflow wykonany (mock)
❌ Brak historii
❌ Brak konwersacji po restarcie
```

### Scenariusz 3: Pełna konfiguracja
```bash
# Konfiguracja
OPENROUTER_API_KEY=sk-or-...
REDIS_URL=redis://localhost:6379/0
# + wszystkie kontenery

# Wynik
✅ Pełne funkcje
✅ Historia
✅ Konwersacje
✅ LLM dla złożonych zapytań
```

System NLP2DSL jest zaprojektowany z myślą o odporności na błędy - może działać w ograniczonym trybie nawet bez pełnej konfiguracji, co pozwala na szybkie rozpoczęcie pracy i stopniowe dodawanie integracji.
