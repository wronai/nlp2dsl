# Przykłady użycia NLP2DSL

Praktyczne scenariusze automatyzacji (faktury, e-mail, raporty, dialog). **Logika każdego przykładu jest w `examples/<nr>/scenario.py`** — `main.py` to cienki punkt wejścia. Wspólne helpery HTTP/print są w `nlp2dsl_sdk/preview.py`.

## Struktura

```
examples/
├── 01-invoice/              # Faktura one-shot
├── 02-email/                # E-mail — parser + quality gate body
├── 03-report-and-notify/    # Raport + email + Slack
├── 04-scheduled-report/     # Harmonogramy (daily/weekly/monthly)
├── 05-conversation-flow/    # Dialog: faktura → uzupełnienie → uruchom
├── 06-interactive-chat/     # Tryb interaktywny w terminalu (-i)
├── 07-email-conversation/   # E-mail z brakującym body — uzupełnienie w dialogu
├── 08-multi-object-benchmark/  # 20 zapytań — invoice/slack/crm/code/…
├── 09-execution-smoke/      # Wykonanie E2E (execute=true) dla 5 typów
├── 10-llm-benchmark/        # 20 zapytań tylko mode=llm (OpenRouter)
├── 11-notify-quality/       # Powiadomienia: quality_required + enrich
├── 12-ir-show/              # MVP workflow vs nlp2dsl show (IntentIR)
└── README.md
```

### Dlaczego wcześniej wszystko było w `demos.py`?

Historycznie `nlp2dsl_sdk/demos.py` był **jednym katalogiem dla CLI `nlp2dsl-demo`** — żeby nie duplikować HTTP, printów i listy demo. To wygodne dla `nlp2dsl-demo gallery`, ale **słabe do nauki**, bo `examples/*/main.py` były tylko wrapperami.

Obecny podział:

| Plik | Rola |
|------|------|
| `examples/02-email/scenario.py` | **Twoja logika** — prompty, kroki, asercje wizualne |
| `examples/02-email/main.py` | `python3 main.py` — uruchomienie |
| `nlp2dsl_sdk/preview.py` | Wspólne `print_workflow_preview`, `preview_text_examples` |
| `nlp2dsl_sdk/demos.py` | Re-eksport do `nlp2dsl-demo` (`load_example_runner`) |

---

## Intract, walidacja i logi

### Czy przykłady `examples/*` używają Intract?

**Nie.** Ścieżka `examples/` → `NLP2DSLClient` → backend `:8010` → nlp-service → worker **nie przechodzi przez Intract**.

| Ścieżka | Walidacja | Intract |
|---------|-----------|---------|
| `examples/*/main.py` (MVP Docker) | Pydantic w nlp-service (`NLPResult`, `WorkflowDSL`), `quality_required` (np. `body` e-maila), status `incomplete` / `complete` | **nie** |
| `nlp2dsl show "…"` | `IntentIR` / `ExecutionPlanIR` (Pydantic) | opcjonalnie `NLP2CMD_INTRACT_GATE=1` w **nlp2cmd** |
| `nlp2cmd plan "…"` | `needs_clarification`, plan gate | opcjonalnie Intract w **nlp2cmd** |

Szczegóły: [`docs/intract-integration.md`](../docs/intract-integration.md).

### Co jest walidowane w przykładach MVP?

1. **Parser** — intent + entities (`/nlp/parse`, tryb `rules` / `llm` / `auto`)
2. **Mapper** — wymagane pola z `ACTIONS_REGISTRY`; `quality_required: [body]` dla e-maila
3. **Odpowiedź API** — `status: complete | incomplete | executed`; SDK sprawdza `execution.steps[].status`
4. **Wykonanie** — worker symuluje akcje; w logach widać `completed` / `failed` per krok

Przykłady **nie robią twardej asercji pytest** na każdy krok — pokazują wynik na stdout (`✅` / `❌`). Testy integracyjne są w `tests/e2e/`.

### Jak są generowane logi?

Serwisy używają **JSON logów** z `X-Request-ID` (śledzenie między backend ↔ nlp-service):

```bash
# Wszystkie serwisy
docker compose logs -f

# Tylko pipeline NLP
docker compose logs -f nlp-service

# Filtrowanie po request_id (z nagłówka odpowiedzi HTTP)
docker compose logs nlp-service 2>&1 | grep '"request_id":"abc123"'
```

Pola w logu: `ts`, `level`, `service`, `request_id`, `logger`, `msg`.  
Kluczowe loggery: `nlp.mapper`, `nlp.enrich`, `nlp.llm`, `orchestrator`.

Poziom: `LOG_LEVEL=DEBUG` w env nlp-service (domyślnie `INFO`).

---

## Szybki start

```bash
cd /path/to/nlp2dsl
docker compose up -d
pip install -e .
./examples/run-all.sh
```

Pojedynczy przykład:

```bash
cd examples/02-email
python3 main.py
```

---

## Tryb interaktywny — rozmowa z nlp2dsl

Użyj gdy dane są **niekompletne** (faktura bez kwoty, e-mail bez body). System dopytuje i buduje DSL dopiero gdy `status=ready`.

### 1. Python SDK (`ConversationFlow`)

```bash
cd examples/06-interactive-chat
python3 main.py --interactive
```

Przepływ w terminalu:

```
👤 Ty: Chcę wysłać fakturę
🤖 System: Podaj: kwotę, adres e-mail odbiorcy
👤 Ty: 1500 PLN na klient@firma.pl
🤖 System: Workflow gotowy: auto_send_invoice (1 kroków). Wyślij 'uruchom' aby wykonać.
👤 Ty: uruchom
```

Słowa kluczowe wykonania: `uruchom`, `wykonaj`, `run`, `tak`, `ok`, `kontynuuj`.

### 2. HTTP API (backend :8010)

```bash
# Start
curl -s -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać fakturę"}' | jq .

# Uzupełnienie (conversation_id z poprzedniej odpowiedzi)
curl -s -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "1500 PLN na klient@firma.pl"}' | jq .

# Wykonanie
curl -s -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "uruchom"}' | jq .
```

### 3. E-mail z brakującym body (przykład 07)

```bash
cd examples/07-email-conversation
python3 main.py
```

Pokazuje różnicę: one-shot `incomplete` vs dialog z uzupełnieniem treści.

### 4. LLM uzupełnia body (bez dialogu)

Gdy `NLP_ENRICH_MISSING=1` i jest `OPENROUTER_API_KEY`, nlp-service sam generuje `body` z kontekstu (Faza B). Dialog nadal działa gdy enrich wyłączony lub LLM niedostępny.

---

## Katalog przykładów

### 01 — Faktura
```bash
python3 examples/01-invoice/main.py
```
One-shot: tekst → DSL → `send_invoice`.

### 02 — E-mail
```bash
python3 examples/02-email/main.py
```
Cztery warianty fraz + wykonanie. Pierwsza fraza (tylko temat) → `incomplete` bez enrich.

### 03 — Raport + powiadomienia
Wielokrokowy workflow: `generate_report` → `send_email` → `notify_slack`.

### 04 — Zaplanowane raporty
Triggery: `daily`, `weekly`, `monthly` + generowanie z tekstu.

### 05 — Konwersacja (faktura)
Skryptowany 3-krokowy dialog. Interaktywnie: `python3 main.py -i`.

### 06 — Interaktywny chat
`python3 main.py -i` — dowolna intencja w pętli. Bez `-i`: krótkie demo (dla `run-all.sh`).

### 07 — E-mail + dialog
One-shot vs conversation dla tego samego promptu z brakującym `body`.

### 08 — Benchmark 20 obiektów
```bash
python3 examples/08-multi-object-benchmark/main.py
python3 examples/08-multi-object-benchmark/main.py --modes rules,auto,llm
```
Mierzy skuteczność NLP→DSL dla: invoice, slack, telegram, teams, crm, report, code, system, composite. Wyniki JSON w `results/`.

### 09 — Smoke wykonania
```bash
python3 examples/09-execution-smoke/main.py
```
5 scenariuszy z `execute=true` — weryfikuje worker end-to-end.

### 10 — Benchmark LLM-only
```bash
python3 examples/10-llm-benchmark/main.py
```
20 zapytań z `mode=llm`. Przy `unknown` z LLM — automatyczny fallback na rules (`resolve_mode.py`).

### 11 — Powiadomienia quality + enrich
```bash
python3 examples/11-notify-quality/main.py
NLP_ENRICH_MISSING=1 python3 examples/11-notify-quality/main.py
```
`Powiadom #oncall` bez treści → `incomplete`; z dwukropkiem lub `o …` → `complete`; enrich uzupełnia gdy włączony.

### 12 — MVP vs IntentIR
```bash
pip install -e . && ./scripts/setup-dev.sh
python3 examples/12-ir-show/main.py
NLP2CMD_INTRACT_GATE=1 nlp2dsl show "znajdź pliki *.py" --plan
```

---

## Wyniki benchmarku (ostatni run)

| Tryb | Pass rate | Uwagi |
|------|-----------|-------|
| `rules` | **20/20 (100%)** | ~0.3s, bez API |
| `auto` | **20/20 (100%)** | rules first, LLM gdy confidence < 0.5 |
| `llm` | **~16–20/20** | zależny od modelu; fallback rules przy unknown |

---

## Schema dynamiczne a LLM

| Warstwa | Źródło | LLM? |
|---------|--------|------|
| Formularze UI (`/actions/schema`) | `ACTIONS_REGISTRY` + `FIELD_TYPES` | nie — deterministyczne |
| Prompt LLM (`parse_llm`) | `prompt_catalog.py` buduje katalog z rejestru | tak — **dynamiczny katalog intencji** |
| DSL (`map_to_dsl`) | mapper deterministyczny | nigdy |

OpenRouter **nie generuje JSON Schema od zera** — rozszerza rozpoznanie intencji i entities wg katalogu z rejestru. Nowa akcja wymaga wpisu w `ACTIONS_REGISTRY` (lub `system_registry_add`).

Opcjonalne uzupełnianie pól: `NLP_ENRICH_MISSING=1` (body e-maila).

---

## Przykłady kodu (skrót)

### One-shot
```python
from nlp2dsl_sdk import NLP2DSLClient

with NLP2DSLClient.from_env() as client:
    result = client.workflow_from_text(
        "Wyślij fakturę na 1500 PLN do klient@firma.pl",
        execute=True,
    )
    print(result["status"], result.get("dsl"))
```

### Dialog
```python
from nlp2dsl_sdk import ConversationFlow

flow = ConversationFlow()
flow.start("Wyślij email do jan@example.com z tematem Status")
flow.send_message("Treść: Wszystko zgodnie z planem.")
flow.send_message("uruchom")
```

### Bezpośrednie DSL
```python
from nlp2dsl_sdk import NLP2DSLClient, workflow_step

with NLP2DSLClient.from_env() as client:
    client.run_workflow(
        name="my_flow",
        steps=[workflow_step("send_email", to="a@b.pl", subject="Hi", body="…")],
    )
```

---

## CLI demo (bez katalogu examples)

```bash
nlp2dsl-demo --list
nlp2dsl-demo email
nlp2dsl-demo interactive-chat
```

Te komendy ładują ten sam `scenario.py` co `examples/*/main.py`.

---

## Konfiguracja

```bash
cp .env.example .env
# OPENROUTER_API_KEY=...     # opcjonalnie LLM
# NLP_ENRICH_MISSING=1       # auto-body e-maila
```

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `NLP2DSL_BACKEND_URL` | `http://localhost:8010` | Gateway |
| `NLP2DSL_NLP_SERVICE_URL` | `http://localhost:8012` | NLP bezpośrednio |
| `NLP_ENRICH_MISSING` | `0` | LLM uzupełnia brakujące body |
| `NLP2DSL_UTF8` | `1` | Auto UTF-8 przy imporcie SDK (wyłącz: `0`) |

### Polskie znaki w terminalu

`examples/bootstrap.py` + import `nlp2dsl_sdk` ustawiają UTF-8 automatycznie — **nie trzeba** `export LANG=C.UTF-8`. Zobacz [`docs/encoding.md`](../docs/encoding.md).

### Artefakty `.nlp2dsl/` (NLP → DSL → CMD → process)

Po każdym `main.py` zapisywany jest katalog `examples/NN-name/.nlp2dsl/`:

- `environment.doql.less` — środowisko (DOQL)
- `commands.testql.toon.yaml` — testy komend (testql)
- `pipeline/*.json|yaml` — odpowiedź API per zapytanie
- `process/*.process.yaml` — warstwowy ślad inferencji

Szczegóły: [`docs/artifacts.md`](../docs/artifacts.md)

```bash
bash run-all.sh
python3 ../scripts/aggregate-example-testql.py   # → testql-scenarios/generated-examples.testql.toon.yaml
```

---

## Wsparcie

- API: http://localhost:8010/docs
- Schema akcji: http://localhost:8010/workflow/actions/schema
- Logi: `docker compose logs -f nlp-service backend worker`
