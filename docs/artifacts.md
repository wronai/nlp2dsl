# Artefakty przykładów (`.nlp2dsl/`)

Każdy `examples/NN-name/` po uruchomieniu `main.py` zapisuje transparentny ślad pipeline:

```
NLP (query) → DSL (workflow) → CMD (service request) → process (execution)
```

## Lokalizacja

```
examples/01-invoice/.nlp2dsl/
├── environment.doql.less      # snapshot zmiennych środowiska (DOQL)
├── commands.testql.toon.yaml  # komendy testql do weryfikacji
├── manifest.yaml              # indeks zapytań i ścieżek artefaktów
├── services.yaml              # dostępne akcje z /workflow/actions
├── pipeline/
│   ├── wyslij-fakture-....json
│   └── wyslij-fakture-....yaml
└── process/
    └── wyslij-fakture-....process.yaml
```

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

Format DOQL (LESS) — deklaracja środowiska bez sekretów (`OPENROUTER_API_KEY` maskowany).

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
