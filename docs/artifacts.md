# Artefakty przykładów (`.nlp2dsl/`)

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
| Domyślny `send_invoice` | **brak** — `attachment_path` opcjonalny, domyślnie pusty | `invoice_id` w `pipeline/*.json` i `workflow_history.last_invoice_id` |
| Autofill z `fixtures/*.pdf` | opcjonalny załącznik w DSL | walidacja MVP (`FAKTURA` lub `%PDF`) gdy path niepusty |
| `attachment_required` + nested generate | `/tmp/nlp2dsl-invoices/INV-*.pdf` (kontener) | j.w. + walidacja kwoty w pliku |
| Upload użytkownika | ścieżka z `attachmentPath` / `context_json` | j.w. |

### Walidacja załącznika

- Ścieżki względne (`fixtures/faktura-2024.pdf`) są **rozwiązywane** względem `NLP2DSL_EXAMPLE_DIR` przed sprawdzeniem `is_file()`.
- **MVP:** akceptowany jest plik tekstowy z nagłówkiem `FAKTURA` i linią `Kwota: …` zgodną z `amount`.
- **Strict:** `NLP2DSL_STRICT_PDF=1` wymaga nagłówka binarnego `%PDF`.
- Pusta `attachment_path` w trybie domyślnym → **brak walidacji pliku** (załącznik opcjonalny; bootstrap nie autofilluje PDF).
- Klient wysyła `example_dir` w `context_json` (mapowany na `/examples/NN-name` w Dockerze), żeby nlp-service mógł rozwiązać `fixtures/…`.
- Docker Compose montuje `./examples:/examples:ro` dla `nlp-service` i `backend`.

Worker **nie** zapisuje PDF do `.nlp2dsl/` w domyślnym MVP.

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
