# Przykłady użycia NLP2DSL

Zbiór praktycznych przykładów pokazujących, jak używać platformy NLP2DSL do automatyzacji procesów biznesowych. Od tej wersji logika HTTP i wspólne flow są wyciągnięte do pakietu `nlp2dsl_sdk`, a skrypty w `examples/` są cienkimi wrapperami nad helperami SDK. Dodatkowo pakiet udostępnia katalog demo i CLI (`nlp2dsl-demo`) do uruchamiania gotowych scenariuszy bez tworzenia boilerplate'u. Jeśli chcesz używać tej samej warstwy w projekcie produkcyjnym, zainstaluj pakiet z repozytorium przez `pip install -e .`.

## Struktura

```
examples/
├── 01-invoice/                # Wysyłanie faktury
├── 02-email/                  # Wysyłanie e-maila
├── 03-report-and-notify/      # Raport + powiadomienia
├── 04-scheduled-report/       # Zaplanowane raporty
├── 05-conversation-flow/      # Konwersacyjny flow
└── README.md                  # Ta dokumentacja
```

## Szybki start

### Lokalne uruchomienie
1. Upewnij się, że platforma działa:
   ```bash
   docker compose up -d
   ```

2. Wybierz przykład i uruchom:
   ```bash
   cd examples/01-invoice
   ./run.sh
   # lub
   python3 main.py
   ```

3. Albo uruchom gotowy demo katalog z pakietu:
   ```bash
   nlp2dsl-demo --list
   nlp2dsl-demo gallery
   nlp2dsl-demo actions
   ```

### Uruchomienie w Dockerze
Każdy przykład zawiera Dockerfile i może być uruchomiony kontenerowo:
```bash
# z katalogu głównego repo
docker build -f examples/01-invoice/Dockerfile -t nlp2dsl-invoice-example .
docker run --rm --network host nlp2dsl-invoice-example
```

## Przykłady

### 1. Wysyłanie Faktury
- **Lokalizacja**: `examples/01-invoice/`
- **Opis**: Prosty przykład wysyłania faktury z kwotą i odbiorcą
- **Koncepcje**: `run_invoice_demo()`, `workflow_from_text()`, `send_invoice()`

### 2. Wysyłanie E-maila
- **Lokalizacja**: `examples/02-email/`
- **Opis**: Różne sposoby wysyłania e-maili
- **Koncepcje**: `run_email_demo()`, `workflow_from_text()`, `send_email()`

### 3. Raport i Powiadomienia
- **Lokalizacja**: `examples/03-report-and-notify/`
- **Opis**: Generowanie raportu i wysyłanie do wielu kanałów
- **Koncepcje**: `run_report_and_notify_demo()`, wielokrokowe workflow, powiadomienia

### 4. Zaplanowane Raporty
- **Lokalizacja**: `examples/04-scheduled-report/`
- **Opis**: Automatyczne raporty według harmonogramu
- **Koncepcje**: `run_scheduled_report_demo()`, triggery, schedule

### 5. Konwersacyjny Flow
- **Lokalizacja**: `examples/05-conversation-flow/`
- **Opis**: Pełny cykl konwersacji od startu do wykonania
- **Koncepcje**: `ConversationFlow`, `run_demo()`, `run_interactive()`, dynamic forms

## Konfiguracja środowiska

### Pliki .env.example
Każdy przykład zawiera plik `.env.example` z opcjonalną konfiguracją:
```bash
cp .env.example .env
# Edytuj .env z swoimi danymi
```

### Opcjonalne serwisy
Niektóre przykłady mogą korzystać z dodatkowych serwisów:
```bash
# SMTP mock (dla emaili i faktur)
docker compose -f examples/docker-compose.yml --profile email up -d smtp-mock
# UI: http://localhost:8025

# Redis (cache i kolejki)
docker compose -f examples/docker-compose.yml --profile cache up -d redis

# PostgreSQL (historia konwersacji)
docker compose -f examples/docker-compose.yml --profile history up -d postgres

# MinIO (storage dla raportów)
docker compose -f examples/docker-compose.yml --profile storage up -d minio
# Console: http://localhost:9001
```

### Prawdziwe integracje
Aby użyć prawdziwych serwisów zamiast mock responses:

1. **Email/SMTP**: Skonfiguruj zmienne w `.env`:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_USER=twoj@gmail.com
   SMTP_PASSWORD=twoj_haslo_aplikacji
   ```

2. **Slack**: Skonfiguruj webhook URL:
   ```env
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

3. **Storage raportów**: Użyj MinIO lub AWS S3:
   ```env
   STORAGE_TYPE=s3
   S3_ENDPOINT=http://localhost:9000
   S3_ACCESS_KEY=minioadmin
   ```

## Korzystanie z SDK

### 1. One-shot API
Najszybszy sposób na wykonanie pojedynczej akcji:
```python
from nlp2dsl_sdk import NLP2DSLClient

with NLP2DSLClient.from_env() as client:
    client.workflow_from_text("Wyślij fakturę na 1500 PLN do klient@firma.pl")
```

### 2. Konwersacyjny flow
Gdy potrzebujesz dopytać o brakujące dane:
```python
from nlp2dsl_sdk import ConversationFlow

flow = ConversationFlow()
flow.run_demo()
# albo:
# flow.run_interactive()
```

### 3. Bezpośrednie DSL
Gdy znasz dokładną konfigurację:
```python
from nlp2dsl_sdk import NLP2DSLClient, workflow_step

with NLP2DSLClient.from_env() as client:
    client.run_workflow(
        name="my_workflow",
        steps=[
            workflow_step("send_invoice", amount=1500, to="klient@firma.pl", currency="PLN"),
            workflow_step("send_email", to="billing@firma.pl", subject="Faktura wysłana"),
        ],
    )
```

### 4. Boilerplate-free demo catalog
Gdy chcesz szybko dodać nowy scenariusz demo bez kopiowania HTTP i printów:
```python
from nlp2dsl_sdk import DEMO_REGISTRY, list_available_demos

for spec in list_available_demos():
    print(spec.name, spec.description)

DEMO_REGISTRY["gallery"]()
```

## Dostępne akcje

| Akcja | Parametry | Przykładowe komendy |
|-------|-----------|-------------------|
| `send_invoice` | `amount`, `to`, `currency` | "Wyślij fakturę", "Wystaw rachunek" |
| `send_email` | `to`, `subject`, `body` | "Wyślij email", "Napisz maila" |
| `generate_report` | `report_type`, `format` | "Generuj raport", "Zestawienie" |
| `crm_update` | `entity`, `data` | "Aktualizuj CRM", "Zmień dane" |
| `notify_slack` | `channel`, `message` | "Powiadom Slack", "Napisz na #" |

## Composite Intents

System automatycznie rozpoznaje złożone intencje:
- `invoice_and_notify` - Faktura + powiadomienie
- `invoice_and_email` - Faktura + email
- `report_and_notify` - Raport + powiadomienia
- `report_and_email` - Raport + email
- `full_invoice_flow` - Pełny proces faktury
- `full_report_flow` - Pełny proces raportu

## Tryby LLM

Domyślnie system używa parsera regułowego (działa bez kluczy API). Można włączyć LLM:

```bash
# Odkomentuj w docker-compose.yml:
# - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
# - LLM_MODEL=openrouter/openai/gpt-5-mini
```

## Testowanie

Każdy przykład zawiera skrypt testowy:
```bash
# Uruchom wszystkie przykłady
for dir in examples/*/; do
    echo "Testing $dir"
    cd "$dir"
    python3 main.py
    cd - > /dev/null
done
```

## Wskazówki

1. **Zacznij od prostych przykładów** - `01-invoice` lub `02-email`
2. **Użyj konwersacyjnego flow** gdy dane są niekompletne
3. **Sprawdź schema** aby zobaczyć dostępne pola:
   ```bash
   curl http://localhost:8010/workflow/actions/schema
   ```
4. **Logi** pomagają zrozumieć działanie:
   ```bash
   docker compose logs -f nlp-service
   ```

## Dodawanie własnych przykładów

1. Najpierw sprawdź, czy istniejący katalog demo w `nlp2dsl_sdk` nie pokrywa Twojego przypadku
2. Jeśli potrzebujesz nowego scenariusza, dopisz go jako nową definicję do katalogu demo albo użyj `workflow_step()` do złożenia workflow
3. Dodawaj tylko cienkie wrappery w `examples/`, jeśli naprawdę potrzebujesz osobnego punktu wejścia
4. Przetestuj przed dodaniem

## Wsparcie

- Dokumentacja API: http://localhost:8010/docs
- Schema akcji: http://localhost:8010/workflow/actions/schema
- Logi: `docker compose logs -f`
