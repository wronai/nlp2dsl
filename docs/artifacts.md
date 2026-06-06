# Artefakty przykładów (`.nlp2dsl/`)

Implementacja: pakiet **[`nlp2dsl-artifacts`](../packages/nlp2dsl-artifacts/)** (mapa DOQL: **[`env2llm`](../../../semcod/env2llm)**).  
`nlp2dsl_sdk.artifacts` to cienki shim — w nowym kodzie importuj `nlp2dsl_artifacts`.

Każdy `examples/NN-name/` po uruchomieniu `main.py` zapisuje transparentny ślad pipeline:

```
NLP (query) → DSL (workflow) → CMD (service request) → process (execution)
```

## Lokalizacja

```
examples/01-invoice/
├── fixtures/invoice-request.txt   ← statyczne (nie kasować przy clean .nlp2dsl)
└── .nlp2dsl/
    ├── registry/environment.doql.less   ← live stan procesu
    ├── runs/{run_id}/turn-NN-{phase}.json
    ├── report/last-run.result.json
    ├── pipeline/*.json
    ├── process/*.process.yaml
    └── result.json                    ← raport TestQL (legacy + report/)
```

Katalog można wyczyścić przed runem: `rm -rf examples/NN/.nlp2dsl/*` — `main.py` odtworzy artefakty.

## Gdzie jest faktura?

| Tryb | Plik PDF | Identyfikator |
|------|----------|---------------|
| Domyślny `send_invoice` (bez attachment) | brak | `invoice_id` w pipeline / `workflow_history` |
| Autofill z `fixtures/*.pdf` | fixture w `examples/NN/fixtures/` | walidacja MVP lub strict |
| `attachment_required` + nested generate | `.nlp2dsl/generated/invoices/INV-*.pdf` | binarny `%PDF-1.4` + walidacja kwoty |
| Upload użytkownika | ścieżka z `context_json` | j.w. |

### Walidacja załącznika

- Ścieżki względne (`fixtures/faktura-2024.pdf`) są **rozwiązywane** względem `NLP2DSL_EXAMPLE_DIR` / mount `/examples`.
- **MVP:** `%PDF` **lub** tekst `FAKTURA` + linia `Kwota: …` zgodna z `amount`.
- **Strict:** `conversation { strict_pdf: true; }` w DOQL **lub** `NLP2DSL_STRICT_PDF=1` — tylko binarny `%PDF`.
- Przykład `01-invoice`: `strict_pdf: true` w `example-profiles.yaml`; `generate_invoice` zapisuje prawdziwy PDF.
- Pusta `attachment_path` gdy załącznik niewymagany → brak walidacji pliku.
- Odpowiedź API zawiera `attachment_validation: { path, resolved, status, issues }`.
- Docker: `./examples:/examples` dla nlp-service (rw), backend i worker (ro).

Worker zapisuje PDF do `.nlp2dsl/generated/invoices/` gdy nested generate / worker `generate_invoice` wskazuje ścieżkę pod example dir.

Pełna architektura: [`validation.md`](validation.md).

## Stan procesu per tura (docelowy model)

Jeden plik źródłowy: **`registry/environment.doql.less`** (mirror: `environment.doql.less`). Pozostałe pliki to raporty / debug.

| Faza (prompt) | `workflow_history.last_phase` | Blok `data` |
|---------------|------------------------------|-------------|
| Bootstrap | — | runtimes/commands z profilu |
| „Wyślij fakturę” | `preflight` / `preflight_autofill` | `send_invoice.amount`, `.to` |
| DSL gotowy | `dsl_ready` | config z workflow |
| „uruchom” | `executed` | `send_invoice.last_invoice_id` |

Odświeżanie: `refresh_doql_registry()` (SDK) po każdej turze w `ConversationFlow`; `finalize()` **scala** obserwacje z istniejącego pliku (`merge_registry_observations`).

## Generowanie

```bash
cd examples
bash run-all.sh                    # wszystkie przykłady + agregacja testql

# pojedynczy przykład
python3 01-invoice/main.py

# zregeneruj zbiorczy testql
python3 ../scripts/aggregate-example-testql.py
# → testql-scenarios/generated-examples.testql.toon.yaml
```

## Moduły

| Plik artefaktu | Pakiet | Funkcja |
|----------------|--------|---------|
| `manifest.yaml`, `pipeline/`, `process/` | `nlp2dsl-artifacts` | `ExampleArtifactWriter`, `build_process_trace` |
| `commands.testql.toon.yaml` | `nlp2dsl-artifacts` | `write_testql_commands` |
| `registry/environment.doql.less` | `env2llm` | `generate_system_map`, `write_registry` |
| `conversation.transcript.md` | `testql-conversations` | `write_conversation_artifacts` |
| `generated/markpact/`, `generated/pactown/` | `workflow-export` | `export_workflow_publish_layer` |
| `generated/docker-compose.stack.yaml` | `nlp2dsl-stack` | `generate_stack_compose` |

## `process/*.process.yaml`

Warstwy:

| layer | opis |
|-------|------|
| `nlp` | parse_intent — status, missing_fields, opcjonalnie IntentIR |
| `dsl` | map_to_workflow — kroki DSL |
| `cmd` | build_service_requests — endpoint/transport per akcja |
| `process` | execute_workflow — wynik worker/system lub blocked |

## `environment.doql.less`

**Mapa systemu** (DOQL) — runtimes, komendy (`runtime`, `protocol`), zasoby, dostępy, artefakty, `data`, reguły `conversation`. Używana przez orchestrator (autofill, attachment gate) i docelowo ProcessAgent.

Szczegóły: [`doql-system-map.md`](doql-system-map.md), [`doql-runtimes.md`](doql-runtimes.md), [`process-agent.md`](process-agent.md).

## `commands.testql.toon.yaml`

Scenariusz testql per przykład:

- `SHELL "cd examples/NN && python3 main.py"`
- `SHELL "nlp2dsl run \"query\" --json"` per zapisane zapytanie

## Walidacja

1. Uruchom przykład → sprawdź `manifest.yaml` (`status`, `actions`, `missing_fields`)
2. Porównaj `pipeline/*.yaml` z oczekiwanym DSL
3. `process/*.process.yaml` — czy warstwa `cmd` wskazuje właściwy serwis
4. `testql` — `testql run testql-scenarios/generated-examples.testql.toon.yaml`

## Wyłączenie

```bash
unset NLP2DSL_EXAMPLE_DIR   # brak zapisu artefaktów (bootstrap ustawia to automatycznie)
```
