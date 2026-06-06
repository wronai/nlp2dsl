# NLP2DSL packages

Monorepo `packages/` — wydzielone biblioteki SDK platformy MVP oraz pakiety integracji **nlp2cmd** ↔ **Propact**.

## Pakiety SDK (artefakty + walidacja)

| Pakiet | Import | Artefakty / rola |
|--------|--------|------------------|
| [`dsl-contracts`](dsl-contracts/) | `dsl_contracts` | `ActionContract`, registry, drafty LLM → `.nlp2dsl/generated/contracts/` |
| [`workflow-export`](workflow-export/) | `workflow_export` | markpact README + pactown ecosystem YAML |
| [`nlp2dsl-stack`](nlp2dsl-stack/) | `nlp2dsl_stack` | `docker-compose.stack.yaml`, cron, `stack.manifest.yaml` |
| [`testql-conversations`](testql-conversations/) | `testql_conversations` | walidacja `.testql.toon.yaml`, `conversation.transcript.md` |
| [`nlp2dsl-artifacts`](nlp2dsl-artifacts/) | `nlp2dsl_artifacts` | `manifest.yaml`, `pipeline/`, `process/`, `commands.testql.toon.yaml` |
| [`dsl-validate`](dsl-validate/) | `dsl_validate` | `ValidationIssue`, pipeline faz walidacji (bez plików — runtime) |

Zewnętrzna zależność mapy środowiska: **[`env2llm`](../../../semcod/env2llm)** (`environment.doql.less`, `SystemMapIR`).

`nlp2dsl_sdk` zachowuje **shimy** (`nlp2dsl_sdk.contracts` → `dsl_contracts`, itd.) — istniejący kod i testy działają bez zmian importów.

```python
# Bezpośrednio z pakietu (zalecane w nowym kodzie)
from dsl_contracts import ActionContract, contract_from_registry_entry
from dsl_validate import ValidationIssue, validate_step_issues
from nlp2dsl_artifacts import ExampleArtifactWriter, build_process_trace
from testql_conversations import validate_conversation_scenario

# Legacy — nadal działa
from nlp2dsl_sdk.contracts import ActionContract
from nlp2dsl_sdk.validation import ValidationIssue
```

## Pakiety IR (nlp2cmd ↔ Propact)

| Pakiet | Import / CLI | Rola |
|--------|--------------|------|
| `pact-ir` | `pact_ir` | Wspólne `IntentIR` i `ExecutionPlanIR` |
| `nlp2cmd-intent` | `nlp2cmd_intent` | Normalizacja, intencja, keyword detector (kanoniczny) |
| `nlp2cmd-planner` | `nlp2cmd_planner` | Strategie planowania → `ExecutionPlanIR` |
| `nlp2cmd-propact` | `nlp2cmd_propact` | IR → Propact markdown + `HybridPlanExecutor` |
| `nlp2dsl-show` | **`nlp2dsl-show`** | Tylko struktura zapytania — bez wykonania |

## Podział odpowiedzialności

| Narzędzie | Zadanie |
|-----------|---------|
| **`nlp2dsl show "query"`** | Struktura zapytania (IntentIR) — SDK CLI, **bez wykonania** |
| **`nlp2dsl-show show "query"`** | To samo (pakiet `nlp2dsl-show`, bez backendu) |
| **`nlp2cmd plan "query"`** | Plan → Propact markdown; `--execute` uruchamia hybrid executor |
| **`nlp2cmd -q "query" -r`** | Legacy runtime (shell / browser / canvas) |
| **`nlp2cmd -q "query" --explain`** | Analiza wejścia (IntentIR) + generowanie |

`nlp2cmd` domyślnie uruchamia analizę nlp2dsl na wejściu (`NLP2CMD_QUERY_INPUT=1`).

`nlp2dsl-run` jest **deprecated** — użyj `nlp2cmd plan`.

## Routing wykonania (`HybridPlanExecutor`)

`nlp2cmd plan --execute` kieruje kroki planu według `target_kind`:

| `target_kind` | Executor | Propact block |
|---------------|----------|---------------|
| `shell` | Propact (lub shell fallback) | ` ```propact:shell` ` |
| `rest`, `mcp`, `ws` | Propact | ` ```propact:rest` ` / `mcp` / `ws` |
| `browser`, `sql`, `desktop` | nlp2cmd `PipelineRunner` | ` ```propact:delegate` ` (marker w MD) |

Podgląd tras: `nlp2cmd plan "…" --explain` lub `--json` (pole `execution_routes`).

## Instalacja (dev)

`env2llm` i pakiety `packages/*` **nie są na PyPI** — `pip install -e .` samo nie wystarczy.

```bash
cd /path/to/nlp2dsl

# pip (project.sh, run-all.sh)
bash scripts/install-local-deps.sh && pip install -e .

# pełny dev (nlp2cmd integration)
./scripts/setup-dev.sh

# uv (rozwiązuje [tool.uv.sources] automatycznie)
uv sync

export NLP2CMD_INTEGRATION=1
```

Wymaga sklonowanego [`env2llm`](../../../semcod/env2llm) obok (`../../semcod/env2llm` od roota nlp2dsl) lub `ENV2LLM_DIR=/ścieżka/do/env2llm`.

## Przykłady

```bash
# Struktura (bez wykonania)
nlp2dsl show "znajdz pliki *.py w src"
nlp2dsl show "znajdz pliki *.py w src" --plan

# Plan + markdown
NLP2CMD_INTEGRATION=1 nlp2cmd plan "znajdz pliki *.py w src"
nlp2cmd plan "znajdz pliki *.py w src" --explain
nlp2cmd plan "znajdz pliki *.py w src" --json

# Wykonanie (shell → Propact lub subprocess fallback)
nlp2cmd plan "znajdz pliki *.py w src" --execute

# Workflow REST (wymaga backendu nlp2dsl)
export NLP2CMD_NLP2DSL_WORKFLOW=1 NLP2DSL_BACKEND_URL=http://127.0.0.1:8010
nlp2cmd plan "Wyslij fakture na 1500 PLN do a@b.pl" --json

# Legacy runtime + analiza wejścia
NLP2CMD_SHOW_STRUCTURE=1 nlp2cmd -q "znajdz pliki *.py w src" --explain
```

## Kolejność zależności

### SDK (artefakty)

```mermaid
flowchart TB
    E2L[env2llm — semcod/env2llm]
    DC[dsl-contracts]
    WE[workflow-export]
    DV[dsl-validate]
    NS[nlp2dsl-stack]
    NA[nlp2dsl-artifacts]
    TQ[testql-conversations]

    E2L --> NS
    E2L --> NA
    E2L --> DV
    DC --> WE
    DC --> DV
```

Kolejność `install-dev.sh`: `dsl-contracts` → `workflow-export` → `nlp2dsl-stack` → `testql-conversations` → `nlp2dsl-artifacts` → `dsl-validate` → pakiety IR.

### IR (nlp2cmd)

```mermaid
flowchart TB
    PI[pact-ir]
    INT[nlp2cmd-intent]
    PL[nlp2cmd-planner]
    PR[nlp2cmd-propact]
    SH[nlp2dsl-show]
    NC[nlp2cmd]

    PI --> INT --> PL --> PR
    INT --> SH
    PL --> SH
    INT --> NC
    PL --> NC
    PR --> NC
    SH -.->|opcjonalny contract_check| NC
```

Browser/desktop/canvas automation pozostaje w legacy runtime **nlp2cmd** (delegacja z hybrid executora).

## Walidacja i Intract

| Warstwa | Pakiet / narzędzie | Intract? |
|---------|-------------------|----------|
| Struktura IR | `pact-ir`, Pydantic | nie |
| Detekcja intencji | `nlp2cmd-intent` | nie |
| Planowanie | `nlp2cmd-planner` | nie |
| Kontrakty planu | `nlp2cmd` + `NLP2CMD_INTRACT_GATE` | tak (`PlanStepGate`) |
| Wykonanie legacy | `nlp2cmd -q -r` | tak (`TransformValidator`, `PipelineRunnerGate`) |

```mermaid
sequenceDiagram
    participant show as nlp2dsl show --plan
    participant intent as nlp2cmd-intent
    participant plan as nlp2cmd-planner
    participant gate as nlp2cmd PlanStepGate

    show->>intent: analyze_query
    intent-->>show: IntentIR
    show->>plan: ExecutionPlanIR
    opt NLP2CMD_INTRACT_GATE=1
        show->>gate: contract_check
        gate-->>show: passed / violations
    end
```

Szczegóły: [`../docs/intract-integration.md`](../docs/intract-integration.md) · pełna architektura runtime: [nlp2cmd/docs/architecture/intract-integration.md](https://github.com/wronai/nlp2cmd/blob/main/docs/architecture/intract-integration.md)

## Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `NLP2CMD_INTEGRATION` | `0` | Włącza `nlp2cmd plan` |
| `NLP2CMD_QUERY_INPUT` | `1` | IntentIR na wejściu każdego zapytania |
| `NLP2CMD_SHOW_STRUCTURE` | `0` | Zawsze pokaż analizę tekstu |
| `NLP2CMD_NLP2DSL_WORKFLOW` | `0` | Planner REST: `/workflow/from-text` (faktury, e-mail) |
| `NLP2DSL_BACKEND_URL` | `http://localhost:8010` | Backend nlp2dsl dla workflow |
| `NLP2DSL_TIMEOUT` | `10` | Timeout HTTP workflow (s) |
| `NLP2CMD_PROPACT_BIN` | `propact` | Ścieżka do CLI Propact |
| `NLP2CMD_PROPACT_FALLBACK` | `shell` | Gdy brak propact: `shell` = subprocess; `error` = błąd |
| `NLP2CMD_INTRACT_GATE` | `0` | `contract_check` w `show --plan`; gate w `nlp2cmd plan` i legacy runtime |
| `NLP2CMD_ENFORCE_CLARIFICATION` | `0` | `show` blokuje `confidence < 0.5` (`plan` — zawsze) |
| `NLP2CMD_POST_CHECK` | `0` | Po `plan --execute`: walidacja stdout (nlp2cmd) |
| `NLP2DSL_UTF8` | `1` | Auto UTF-8 w CLI/SDK (`0` = wyłącz) |

## Publikacja (PyPI)

```bash
make build-all    # root SDK + wszystkie pakiety
make publish      # twine upload wszystkiego
```
