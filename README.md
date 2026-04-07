# MVP Automation Platform


## AI Cost Tracking

![AI Cost](https://img.shields.io/badge/AI%20Cost-$1.35-green) ![AI Model](https://img.shields.io/badge/AI%20Model-openrouter%2Fqwen%2Fqwen3-coder-next-lightgrey)

This project uses AI-generated code. Total cost: **$1.3500** with **9** AI commits.

Generated on 2026-04-07 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/models/openrouter/qwen/qwen3-coder-next)

---

> System kompilujący intencje biznesowe (język naturalny) do wykonywalnych procesów w kontenerach Docker — z konwersacyjnym AI i dynamicznym UI.

## Architektura

```
Użytkownik (tekst / głos / GUI)
        │
        ▼
┌──────────────────────────┐
│   NLP Service            │
│  ├─ Parser (rules/LLM)   │  ← rozumie język naturalny
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
git clone <repo-url> && cd nlp2dsl
cp .env.example .env
# Uzupełnij klucze API (opcjonalne - system działa z parserem reguł)
docker compose up --build
```

| Serwis | URL | Opis |
|--------|-----|------|
| Backend API | http://localhost:8010/docs | Gateway + workflow engine |
| NLP Service | http://localhost:8002/docs | NLP + conversation + schema |
| Worker | http://localhost:8004/docs | Executory akcji |

## Conversation Loop (AI Dialog)

System prowadzi konwersację, dopytuje o brakujące dane i generuje dynamiczny formularz UI.

### Rozpocznij rozmowę

```bash
# Tekst
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać fakturę"}'

# Audio (STT via Deepgram)
curl -X POST http://localhost:8010/workflow/chat/start \
  -F "audio=@nagranie.wav"
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
# Tekst
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "a1b2c3d4e5f6", "text": "1500 PLN na klient@firma.pl"}'

# Audio (STT via Deepgram)
curl -X POST http://localhost:8010/workflow/chat/message \
  -F "conversation_id=a1b2c3d4e5f6" \
  -F "audio=@odpowiedz.wav"
```

### Uruchom workflow

```bash
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "a1b2c3d4e5f6", "text": "uruchom"}'
```

## Schema-driven UI

Backend generuje schematy formularzy dynamicznie z rejestru akcji:

```bash
# Wszystkie akcje
curl http://localhost:8010/workflow/actions/schema

# Konkretna akcja
curl http://localhost:8010/workflow/actions/schema/send_invoice
```

Frontend renderuje formularze automatycznie z tych schematów — zero ręcznych formularzy.

## One-shot Pipeline (bez dialogu)

```bash
# Generuj DSL
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl"}'

# Generuj + wykonaj
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl", "execute": true}'
```

## Bezpośrednie uruchomienie DSL (JSON)

```bash
curl -X POST http://localhost:8010/workflow/run \
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

## Speech-to-Text (Deepgram)

System obsługuje wejście głosowe w Conversation Loop:

```bash
# Konfiguracja w .env
DEEPGRAM_API_KEY=

# Użycie
curl -X POST http://localhost:8010/workflow/chat/start \
  -F "audio=@nagranie.wav"
```

### Obsługiwane formaty audio:
- WAV, MP3, M4A, OGG, FLAC
- Język: polski (domyślny), konfigurowalny
- Model: nova-3-general (Deepgram)

### Streaming STT:
Dla konwersacji w czasie rzeczywistym użyj WebSocket:
```python
from audio_parser import StreamingSTT

stt = StreamingSTT(language="pl")
await stt.start()
await stt.send_audio(chunk)
transcript = await stt.get_transcript()
```

## Voice Chat UI (PWA)

System zawiera gotowy interfejs webowy z obsługą głosową:

```bash
# Otwórz w przeglądarce
http://localhost:8002/chat
```

### Funkcje:
- 🎤 **Voice input** - kliknij Start Voice i mów
- 📝 **Text input** - wpisz wiadomość ręcznie
- 🔄 **Real-time** - WebSocket streaming
- 📱 **PWA** - instaluj jako aplikację mobilną/desktopową

### Automatyczny start:
```html
<!-- Auto-connect i auto-voice na onload -->
<body onload="initVoice()">
```

### Kiosk mode (desktop/embedded):
```bash
# Chrome kiosk
chrome --kiosk --autoplay-policy=no-user-gesture-required http://localhost:8002/chat

# Electron app
npm install electron
# main.js: win.loadURL('http://localhost:8002/chat')
```

## Tauri desktop wrapper
 
 Jeśli chcesz desktopową powłokę zamiast samej przeglądarki, użyj wrappera w `tauri-wrapper/`.
 Ten projekt otwiera istniejący backendowy ekran `/chat`, więc nie duplikuje logiki STT/TTS.
 W trybie dev wrapper uruchamia lokalny launcher na `http://127.0.0.1:1420`, a potem przechodzi do backendowego czatu, gdy `/health` odpowie OK.

Jeśli na Twoim Linuxie Tauri blokują brakujące biblioteki WebKitGTK/GTK, użyj browserowego fallbacku:
`cd tauri-wrapper && npm run desktop` albo `bash ./desktop.sh`.
Otwiera on ten sam `/chat` w Chrome/Chromium w trybie `--app`.

### Linux prerequisites
Na Linuxie Tauri v1 wymaga systemowych bibliotek WebKitGTK/GTK. Jeśli `npm run dev` kończy się błędem z brakującymi `libsoup-2.4` albo `javascriptcoregtk-4.0`, doinstaluj:
```bash
sudo apt install build-essential curl wget file libssl-dev libgtk-3-dev \
  libwebkit2gtk-4.0-dev libsoup2.4-dev libjavascriptcoregtk-4.0-dev \
  libayatana-appindicator3-dev librsvg2-dev
```
Jeśli używasz innej dystrybucji, zainstaluj odpowiednie odpowiedniki pakietów deweloperskich WebKitGTK/GTK.

### Uruchomienie

```bash
cd tauri-wrapper
npm install
npm run dev
```

Jeśli nie chcesz instalować bibliotek systemowych albo Tauri nie startuje, użyj:

```bash
cd tauri-wrapper
npm run desktop
```

Launcher sprawdza backend pod `http://127.0.0.1:8002` i dopiero potem przełącza do `http://127.0.0.1:8002/chat`.

### Build

```bash
cd tauri-wrapper
npm run build
```

### Desktop fallback launcher

Jeśli chcesz ominąć Tauri na danym systemie, użyj `tauri-wrapper/desktop.sh`.
Skrypt czeka na backend, a potem otwiera voice chat w Chrome/Chromium w trybie `--app`.
To dobre rozwiązanie, gdy środowisko nie ma wymaganych bibliotek WebKitGTK dla Tauri.

Konfiguracja LLM:

1. Skopiuj `.env.example` → `.env`
2. Uzupełnij klucz API wybranego providera:

```env
# OpenRouter (domyślny)
OPENROUTER_API_KEY=
LLM_MODEL=openrouter/openai/gpt-5-mini

# Speech-to-Text (Deepgram)
DEEPGRAM_API_KEY=

# Lub OpenAI
OPENAI_API_KEY=
LLM_MODEL=gpt-4o-mini

# Lub Anthropic
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-4-...

# Lub Ollama (lokalny)
OLLAMA_API_BASE=http://localhost:11434
LLM_MODEL=ollama/llama3
```

Zmienne są automatycznie przekazywane do kontenerów w `docker-compose.yml`.

## Struktura projektu

```
nlp2dsl/
├── docker-compose.yml
├── .env.example                 # Konfiguracja LLM i serwisów
├── examples/                    # Przykłady użycia
│   ├── 01-invoice/
│   ├── 02-email/
│   ├── 03-report-and-notify/
│   ├── 04-scheduled-report/
│   ├── 05-conversation-flow/
│   ├── README.md
│   ├── EXECUTION_REPORT.md
│   └── MISSING_CONFIGURATION.md
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
├── tauri-wrapper/               # Desktop wrapper Tauri dla `/chat`
└── README.md
```

## Przykłady użycia

Zobacz `examples/README.md` dla pełnej listy przykładów:

Jeśli chcesz od razu uruchomić gotowy scenariusz bez tworzenia wrappera, użyj pakietowego CLI:

```bash
nlp2dsl-demo --list
nlp2dsl-demo gallery
```

```bash
# Uruchom wszystkie przykłady
cd examples
for dir in */; do
    echo "Testing $dir"
    cd "$dir"
    python3 main.py
    cd - > /dev/null
done
```

### Dostępne przykłady:

| Przykład | Link | Opis | Koncepcje |
|----------|------|------|-----------|
| **01-invoice** | [📁 examples/01-invoice/](examples/01-invoice/) | Wysyłanie faktur z kwotą i odbiorcą | One-shot API, DSL |
| **02-email** | [📁 examples/02-email/](examples/02-email/) | Różne sposoby wysyłania e-maili | Aliasy komend, parametry |
| **03-report-and-notify** | [📁 examples/03-report-and-notify/](examples/03-report-and-notify/) | Raporty + powiadomienia na wiele kanałów | Composite intents, multi-step |
| **04-scheduled-report** | [📁 examples/04-scheduled-report/](examples/04-scheduled-report/) | Zaplanowane raporty (daily/weekly/monthly) | Triggers, schedule |
| **05-conversation-flow** | [📁 examples/05-conversation-flow/](examples/05-conversation-flow/) | Pełny cykl konwersacyjny od startu do wykonania | Chat API, state management |

#### Szybki start z przykładami:
```bash
cd examples/01-invoice
python3 main.py
```

## Obsługa błędów i fallback

System jest odporny na brakującą konfigurację:

- **Brak kluczy LLM**: Automatycznie używa parsera reguł
- **Brak Redis**: In-memory storage (utrata danych przy restarcie)
- **Brak bazy**: Ograniczone funkcje (brak historii)
- **Mock integracje**: Worker zwraca symulowane odpowiedzi

Szczegóły w `examples/MISSING_CONFIGURATION.md`.

## Docker i .env

Każdy przykład zawiera:
- `Dockerfile` - konteneryzacja
- `requirements.txt` - zależności Python
- `.env.example` - szablon konfiguracji

Opcjonalne serwisy pomocnicze:
```bash
docker compose -f examples/docker-compose.yml --profile email up -d smtp-mock
docker compose -f examples/docker-compose.yml --profile storage up -d minio
```

## Dodanie nowej akcji

1. `nlp-service/app/registry.py` — dodaj do `ACTIONS_REGISTRY`
2. `worker/worker.py` — dodaj handler `@action("nazwa")`
3. `docker compose up --build`


## License

Licensed under Apache-2.0.
