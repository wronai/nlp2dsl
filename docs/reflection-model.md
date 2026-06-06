# Model refleksji (ReflectionReport)

Nlp2dsl realizuje request w pętli **model → decyzja → refleksja → (pytanie kontekstowe | następny krok)**.

## Fazy

| Faza | Kiedy | Co porównujemy |
|------|--------|----------------|
| `preflight` | Po ProcessAgent autofill | entities vs `TargetPlan` z DOQL |
| `dsl_ready` | DSL complete | config kroku vs mapa + walidacja formatów |
| `validation_failed` | Błąd step_validator | issues + `context_queries` |
| `incomplete` | Braki w polach | missing + propozycje autofill/generate |
| `executed` | Po workerze | obserwacja w registry + `attachment_validation` (post-exec) |

## Artefakty

```
.nlp2dsl/runs/{run_id}/
  turn-01-ready.json
  reflect-01-ready.json      ← ReflectionReport
```

## SDK

```python
from nlp2dsl_sdk.reflection import build_target_plan, reflect_from_chat_turn
from nlp2dsl_sdk.system_map_bridge import doql_file_to_system_map

ir = doql_file_to_system_map(path)
target = build_target_plan(ir, "send_invoice", entities)
report = reflect_from_chat_turn(ir, chat_response, "dsl_ready")

if not report.ready:
    print(report.primary_context_query)  # pętla kontekstowa
```

## Autonomiczna pętla (`autonomous_loop.py`)

Gdy `conversation.autofill: true` (domyślnie), **jedno zadanie** uruchamia wewnętrzną pętlę:

```
validate → autofill(data) → skan fixtures/artifacts → generate_invoice → validate → naprawa invalid PDF → …
```

Przy `strict_pdf` lub błędzie formatu: usuń zły plik z `.nlp2dsl/generated/`, wygeneruj ponownie, waliduj — bez pytania użytkownika (resolution `generate`).

Pyta użytkownika **dopiero gdy** strategie autonomiczne się wyczerpią.

### SDK

```python
from nlp2dsl_sdk.autonomous_flow import AutonomousFlow

flow = AutonomousFlow(client)
result = flow.run_task("Wyślij fakturę")  # autofill + opcjonalnie execute
```

Env: `NLP2DSL_AUTO_EXECUTE=1` (domyślnie) — backend wykonuje workflow po `ready`.

### DOQL

```less
conversation {
  autofill: true;
  sync_auto_execute: true;
  generate_invoice_if_missing: true;
  strict_pdf: true;   /* opcjonalnie — wymaga binarnego %PDF */
}
```

Env: `NLP2DSL_AUTO_EXECUTE=1` (domyślnie) — backend wykonuje workflow po `ready`.  
SDK: `wait_for_health()` czeka na backend `:8010`, nlp `:8012`, worker `:8004` (`NLP2DSL_HEALTH_TIMEOUT`).

## Uproszczenia w `01-invoice`

- `nlp2dsl_sdk.example_bootstrap.ensure_doql_registry()` zamiast duplikatu w `scenario.py`
- `generate_invoice` zapisuje **binarny PDF** (`invoice_pdf.py`), nie tekst z rozszerzeniem `.pdf`
- Walidacja: `nlp2dsl_sdk.step_validation` + `nlp-service/app/validation/step_validator.py`
- `strict_pdf: true` w profilu `01-invoice` (`example-profiles.yaml`)

Zob. też [`validation.md`](validation.md), [`process-agent.md`](process-agent.md).

Pełny stack compose + cron: [`autonomous-stack.md`](autonomous-stack.md) — przykład [`13-autonomous-invoice-stack`](../examples/13-autonomous-invoice-stack/).
