# MVP Automation Platform

> System kompilujący intencje biznesowe (język naturalny) do wykonywalnych procesów w kontenerach Docker — z konwersacyjnym AI i dynamicznym UI.

## Architektura

```
Użytkownik (tekst / głos / GUI)
        │
        ▼
┌──────────────────────────┐
│   NLP Service            │
│  ├─ Parser (rules/LLM)  │  ← rozumie język naturalny
│  ├─ Mapper (determ.)     │  ← buduje DSL
│  ├─ Orchestrator         │  ← conversation loop
│  └─ Schema generator     │  ← dynamic UI forms
└──────────┬───────────────┘
           ▼
┌──────────────────┐     ┌──────────────┐
│     Backend      │────▶│    Worker    │
│  (API Gateway)   │     │  (Executors) │
│  DSL Engine      │     └──────────────┘
└──────┬───────────┘
       │
  ┌────┴────┐
  │ Postgres│
  └─────────┘
```

**Zasada:** LLM rozumie → Pydantic waliduje → Mapper buduje → Docker wykonuje

## Szybki start

```bash
git clone <repo-url> && cd mvp-automation
docker compose up --build
```

| Serwis | URL | Opis |
|--------|-----|------|
| Backend API | http://localhost:8000/docs | Gateway + workflow engine |
| NLP Service | http://localhost:8002/docs | NLP + conversation + schema |
| Worker | http://localhost:8001/docs | Executory akcji |

## Conversation Loop (AI Dialog)

System prowadzi konwersację, dopytuje o brakujące dane i generuje dynamiczny formularz UI.

### Rozpocznij rozmowę

```bash
curl -X POST http://localhost:8000/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać fakturę"}'
```

Odpowiedź (brakujące dane):
```json
{
  "conversation_id": "a1b2c3d4e5f6",
  "status": "in_progress",
  "message": "Podaj: kwotę, adres e-mail odbiorcy",
  "missing": ["send_invoice.amount", "send_invoice.to"],
  "form": {
    "action": "send_invoice",
    "fields": [
      {"name": "amount", "type": "number", "label": "Kwota", "required": true},
      {"name": "to", "type": "email", "label": "Adres e-mail odbiorcy", "required": true},
      {"name": "currency", "type": "select", "label": "Waluta", "required": false, "options": ["PLN","EUR","USD","GBP"]}
    ]
  }
}
```

### Uzupełnij dane

```bash
curl -X POST http://localhost:8000/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "a1b2c3d4e5f6", "text": "1500 PLN na klient@firma.pl"}'
```

### Uruchom workflow

```bash
curl -X POST http://localhost:8000/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "a1b2c3d4e5f6", "text": "uruchom"}'
```

## Schema-driven UI

Backend generuje schematy formularzy dynamicznie z rejestru akcji:

```bash
# Wszystkie akcje
curl http://localhost:8000/workflow/actions/schema

# Konkretna akcja
curl http://localhost:8000/workflow/actions/schema/send_invoice
```

Frontend renderuje formularze automatycznie z tych schematów — zero ręcznych formularzy.

## One-shot Pipeline (bez dialogu)

```bash
# Generuj DSL
curl -X POST http://localhost:8000/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl"}'

# Generuj + wykonaj
curl -X POST http://localhost:8000/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl", "execute": true}'
```

## Bezpośrednie uruchomienie DSL (JSON)

```bash
curl -X POST http://localhost:8000/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "invoice_and_email",
    "steps": [
      {"action": "send_invoice", "config": {"amount": 1500, "to": "klient@firma.pl", "currency": "PLN"}},
      {"action": "send_email", "config": {"to": "klient@firma.pl", "subject": "Faktura wystawiona"}}
    ]
  }'
```

## Dostępne akcje

| Akcja | Wymagane | Aliasy PL |
|-------|----------|-----------|
| `send_invoice` | `amount`, `to` | faktura, rachunek |
| `send_email` | `to` | email, maila, napisz |
| `generate_report` | `report_type` | raport, zestawienie |
| `crm_update` | `entity` | aktualizuj crm |
| `notify_slack` | `channel` | powiadom, slack |

### Composite intents (auto-wykrywane)

`invoice_and_notify` · `invoice_and_email` · `report_and_email` · `full_invoice_flow` · `full_report_flow`

## Tryby NLP

| Mode | Opis |
|------|------|
| `rules` | Offline, regex + aliasy (domyślny) |
| `llm` | LLM API (OpenAI / Anthropic / Ollama) |
| `auto` | Rules first, LLM fallback |

Konfiguracja LLM w `docker-compose.yml` (odkomentuj):
```yaml
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
- OPENAI_API_KEY=${OPENAI_API_KEY}
- OLLAMA_URL=http://ollama:11434
```

## Struktura projektu

```
mvp-automation/
├── docker-compose.yml
├── backend/                     # API Gateway + Workflow Engine
│   └── app/
│       ├── main.py
│       ├── schemas.py           # DSL models (Pydantic)
│       └── workflow.py          # Engine + Chat proxy + Schema proxy
├── nlp-service/                 # NLP → DSL Pipeline
│   └── app/
│       ├── main.py              # FastAPI endpoints
│       ├── schemas.py           # NLP + DSL + Conversation + UI schemas
│       ├── registry.py          # Actions registry (source of truth)
│       ├── parser_rules.py      # Rule-based parser (offline)
│       ├── parser_llm.py        # LLM-based parser (API)
│       ├── mapper.py            # Deterministic NLP → DSL mapper
│       └── orchestrator.py      # Conversation loop + schema-driven UI
├── worker/                      # Imperatywne executory
│   └── worker.py
└── README.md
```

## Dodanie nowej akcji

1. `nlp-service/app/registry.py` — dodaj do `ACTIONS_REGISTRY`
2. `worker/worker.py` — dodaj handler `@action("nazwa")`
3. `docker compose up --build`

## Licencja

MIT


## License

Licensed under Apache-2.0.
