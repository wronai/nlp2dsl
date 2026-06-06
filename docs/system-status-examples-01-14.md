# Stan systemu: przykłady 01-14 i publish layer

Ten dokument podsumowuje aktualny stan platformy po refaktoryzacji lifecycle,
idempotencji wykonania oraz dodaniu warstwy eksportu markpact/pactown.

## Stan systemu

Platforma działa w ścieżce:

```text
NL -> intent -> DSL -> backend validation -> workflow execute -> worker
```

Najważniejsze potwierdzone obszary:

| Obszar | Wynik |
|--------|-------|
| `03-report-and-notify` | `full_report_flow`: report -> email -> Slack |
| `04-scheduled-report` | 4 zapytania NL mapowane do `report_and_email`, triggery `daily` / `weekly` / `monthly` |
| `05-07` conversation | Multi-turn: faktura/e-mail z uzupełnianiem brakujących pól |
| `08-multi-object-benchmark` | Benchmark rules/auto przechodzi jako przykład |
| `09-execution-smoke` | Smoke E2E dla wykonania workflow przechodzi jako przykład |
| `10-llm-benchmark` | LLM benchmark jest częścią suite; wymaga poprawnej konfiguracji LLM |
| `13-autonomous-invoice-stack` | Autonomiczny stack faktury działa w agregacie przykładów |
| `14-markpact-export` | Eksportuje `report_and_email` do markpact + pactown |

Agregat TestQL z `examples/testql-results.json` raportuje obecnie:

| Metryka | Wartość |
|---------|---------|
| Przykłady z wynikiem TestQL | 13 |
| Passed | 13 |
| Failed | 0 |
| Warning | 0 |

Uwaga: przykład `14-markpact-export` jest uruchamiany przez `examples/run-all.sh`, ale
nie jest klasycznym scenariuszem TestQL workflow; jego główna walidacja to testy exportu
oraz opcjonalny parser markpact/pactown.

## Co zaimplementowano

### 1. Lifecycle workflow w backendzie

Dodane jawne etapy API:

| Endpoint | Rola |
|----------|------|
| `POST /workflow/plan` | NL -> plan lifecycle + walidacja DSL |
| `POST /workflow/validate` | Walidacja DSL bez wykonania |
| `POST /workflow/execute` | Walidacja + `dry_run` albo wykonanie |

Wspólne helpery backendowe są w:

| Plik | Rola |
|------|------|
| `backend/app/workflow_lifecycle.py` | Adaptery lifecycle: walidacja, extraction `workflow`/`dsl`, `RunWorkflowRequest` |
| `backend/app/idempotency.py` | Memory/Postgres idempotency store dla `/workflow/execute` |

### 2. Idempotencja side effects

`/workflow/execute` obsługuje `idempotency_key`.

Zachowanie:

| Przypadek | Wynik |
|-----------|-------|
| Pierwszy request z kluczem | Workflow jest wykonywany, wynik zapisywany |
| Ten sam klucz + ten sam workflow | Replay poprzedniego wyniku, `idempotent_replay: true` |
| Ten sam klucz + inny workflow | `409 idempotency_key_conflict` |
| Ten sam klucz, wykonanie jeszcze trwa | `409 idempotency_key_in_progress` |

Store:

| Środowisko | Store |
|------------|-------|
| `POSTGRES_URL` ustawiony | `workflow_idempotency` w Postgres |
| Brak `POSTGRES_URL` | In-memory fallback |

### 3. Moduł export

Nowy pakiet SDK:

```text
nlp2dsl_sdk/export/
  markpact.py
  pactown.py
  publish.py
```

| Plik | Rola |
|------|------|
| `markpact.py` | `ActionContract` + DSL -> README, kontrakty YAML, workflow spec |
| `pactown.py` | `nlp2dsl-platform.pactown.yaml` + stub README serwisów |
| `publish.py` | Wspólny helper dla przykładów i artefaktów: katalog akcji, export, walidacja, output |

Eksport markpact/pactown: pakiet `workflow-export` (`nlp2dsl_sdk.export` = shim). Root `pyproject.toml` deklaruje zależności editable z `packages/`.

### 4. Przykład 14: markpact export

Struktura:

```text
examples/14-markpact-export/
  main.py
  scenario.py
  README.md
  .nlp2dsl/generated/
    markpact/
      README.md
      contracts/
      workflows/
    pactown/
      nlp2dsl-platform.pactown.yaml
      services/
```

Przepływ:

1. Pobiera katalog akcji z `/nlp/actions`, z fallbackiem w SDK.
2. Planuje DSL dla zapytania:
   `Codziennie o 9:00 raport sprzedaży PDF i wyślij email do manager@firma.pl`.
3. Eksportuje markpact + pactown.
4. Opcjonalnie waliduje lokalnymi paczkami `markpact` i `pactown`.

### 5. Auto-export w przykładzie 04

`examples/04-scheduled-report/scenario.py` po udanym planowaniu/wykonaniu eksportuje
publish layer dla workflow `report_and_email`.

Artefakty:

```text
examples/04-scheduled-report/.nlp2dsl/generated/
  markpact/
    README.md
    contracts/generate_report.contract.yaml
    contracts/send_email.contract.yaml
    workflows/report_and_email.workflow.yaml
    workflows/report_and_email.dsl.json
  pactown/
    nlp2dsl-platform.pactown.yaml
    services/
```

## Wygenerowany workflow

Przykład eksportowanego DSL dla `report_and_email`:

```yaml
name: report_and_email
trigger: daily
steps:
  - action: generate_report
    config:
      report_type: sales
      format: pdf
  - action: send_email
    config:
      to: manager@firma.pl
      subject: Automatyczna wiadomość
      body: W załączeniu przesyłamy raport sales.
```

## Jak uruchomić

Pełny suite przykładów:

```bash
cd examples
bash run-all.sh
```

Tylko przykład 14:

```bash
cd examples/14-markpact-export
python3 main.py
```

Walidacja pactown po eksporcie:

```bash
cd examples/14-markpact-export/.nlp2dsl/generated/pactown
pactown validate nlp2dsl-platform.pactown.yaml
```

Lokalne paczki opcjonalne:

```bash
pip install -e ~/github/wronai/markpact -e ~/github/wronai/pactown
```

Smoke idempotencji `/workflow/execute`:

```bash
curl -sS -X POST http://localhost:8010/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "idempotency_smoke",
      "trigger": "manual",
      "steps": [
        {
          "action": "generate_report",
          "config": {"report_type": "sales", "format": "csv"}
        }
      ]
    },
    "idempotency_key": "example-key-1"
  }'
```

Powtórzenie identycznego requestu powinno zwrócić `idempotent_replay: true`.

## Architektura publish layer

```text
nlp2dsl authority
  - parse / plan / validate / execute
  - kontroluje side effects
  - wymusza idempotency_key dla retry-safe wykonania

markpact review layer
  - README
  - kontrakty akcji
  - workflow YAML/JSON
  - testy HTTP, bez wykonywania side effects

pactown compose layer
  - ecosystem manifest
  - opis serwisów platformy
  - sandbox/deploy composition
```

Markpact nie wykonuje side effects. Wykonanie zostaje w backendzie przez
`/workflow/validate` i `/workflow/execute`.

## Weryfikacja

Ostatni sprawdzony zestaw:

```text
backend tests              73 passed
root SDK tests             111 passed
tests/test_export_markpact 4 passed
python3 -m build .         OK
examples TestQL aggregate  13 passed / 0 failed / 0 warning
```

Smoke na realnym Docker/Postgres potwierdził:

| Test | Wynik |
|------|-------|
| Pierwszy `/workflow/execute` z `idempotency_key` | `executed` |
| Drugi identyczny request | `idempotent_replay: true` i ten sam `workflow_id` |
| Ten sam klucz z innym workflow | `409 idempotency_key_conflict` |
| Tabela Postgres | `workflow_idempotency` |

## Następne kroki

1. Dodać TTL/cleanup dla rekordów `workflow_idempotency`.
2. Dodać natywny blok `markpact:actions`, żeby kontrakty akcji nie musiały być tylko `markpact:file`.
3. Podpiąć `export_workflow_publish_layer()` jako opcjonalny hook w `artifacts.py`.
4. Domknąć `POST /workflow/simulate` jako brakujący etap między `validate` i `execute`.
5. Rozszerzyć TestQL o przykład 14 jako osobny check publish/export.
