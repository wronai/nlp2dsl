# Dynamic system map generation (LLM + Pydantic)

## Problem

Dziś `environment.doql.less` jest składany **statycznie w kodzie**:

| Warstwa | Hardcode |
|---------|----------|
| `commands[N]` | `ACTIONS_REGISTRY`, `load_commands_from_services_yaml()` |
| `resources[N]` | ręczny parse `nlp2dsl.yaml` w `load_platform_map()` |
| `access[N]` | grants z YAML |
| `artifacts[N]` | skan `fixtures/` + regex metadanych |
| Pydantic pól | `NLPEntities`, `registry.py` — stała lista pól |
| Protokoły CMD | `_command_transport()` — if/else w Pythonie |

To działa jako **bootstrap MVP**, ale nie spełnia istoty nlp2dsl: mapa systemu powinna powstawać **w locie**, gdy LLM widzi aktualny kontekst (Docker, API, pliki, historia) i emituje **walidowalne struktury**.

## Docelowy przepływ

```mermaid
flowchart TB
  subgraph introspect [Introspection]
    API["GET /workflow/actions<br/>GET /health<br/>GET /workflow/history"]
    FS[filesystem / Mullm listing]
    DOCK[docker compose profiles]
    YAML[nlp2dsl.yaml hints]
  end

  subgraph llm [SystemMapGenerator — LLM]
    PROMPT[Prompt + JSON schema SystemMapIR]
    EMIT[SystemMapIR JSON]
  end

  subgraph validate [Pydantic + protocols]
    IR[SystemMapIR v1]
    MODELS[Dynamic Command input_model<br/>InvoiceDocument, SendInvoiceConfig…]
    MIME[mime.type + schema_ref per field/artifact]
    PROTO[ProtocolSpec → propact:rest | workflow/run]
  end

  subgraph consume [Structure generation]
    DOQL[environment.doql.less]
    DSL[WorkflowDSL steps]
    CMD[PlanStep / worker calls]
    PREF[preflight / autofill]
  end

  introspect --> PROMPT
  PROMPT --> EMIT
  EMIT --> IR
  IR --> MODELS
  IR --> MIME
  IR --> PROTO
  IR --> DOQL
  IR --> PREF
  IR --> DSL
  DSL --> CMD
```

## SystemMapIR (`nlp2dsl.system_map.v1`)

Kanoniczny format mapy — Pydantic w `nlp2dsl_sdk/system_map_ir.py`:

| Typ | Rola |
|-----|------|
| `MimeTypeSpec` | `application/pdf` + `schema_ref: InvoiceDocument` |
| `RuntimeSpecIR` | `executor:worker`, status, roles, docker_profile |
| `ProtocolSpec` | `propact:rest`, `workflow/run`, transport |
| `FieldSpec` | pole komendy + opcjonalny MIME/schema |
| `CommandSchemaIR` | CMD layer — `input_model` generowany przez LLM |
| `ResourceSpecIR` | obszar zasobów + dozwolone MIME |
| `AccessGrantIR` | agent + resource_area + actions |
| `ArtifactSpecIR` | plik + mime + wartości |
| `SystemMapIR` | cała mapa |

Przykład JSON (fragment):

```json
{
  "format": "nlp2dsl.system_map.v1",
  "example_id": "01-invoice",
  "commands": [{
    "name": "send_invoice",
    "runtime": "executor:worker",
    "protocol": {"name": "workflow/run", "transport": "gateway:backend→executor:worker"},
    "input_model": "SendInvoiceConfig",
    "fields": [
      {"name": "amount", "required": true},
      {"name": "to", "required": true},
      {"name": "attachment_path", "required": false,
       "mime": {"type": "application/pdf", "schema_ref": "InvoiceDocument"}}
    ]
  }],
  "artifacts": [{
    "path": "fixtures/faktura-2024.pdf",
    "mime": {"type": "application/pdf", "schema_ref": "InvoiceDocument"}
  }]
}
```

## Generowanie modeli Pydantic w locie

LLM nie powinien pisać DOQL ręcznie — powinien zwrócić **SystemMapIR**, a runtime:

1. **`model_json_schema()`** — export schematu do promptu / Intract
2. **`create_model()`** — dynamiczne `SendInvoiceConfig`, `InvoiceDocument` z `FieldSpec` + `MimeTypeSpec`
3. **Walidacja kroku** — `SystemMapIR.validate_step_config(action, config)` zamiast `registry.get_required_fields()`
4. **Render DOQL** — `render_system_map_doql(ir)` — widok dla człowieka i TestQL

Powiązanie z istniejącymi warstwami:

| Istniejące | Docelowe użycie |
|------------|-----------------|
| `IntentIR` / `ExecutionPlanIR` (pact-ir) | plan wykonania po mapie |
| `TargetKind.propact_protocol` | mapowanie `ProtocolSpec.name` |
| `propact:rest` / `propact:shell` (nlp2cmd-propact) | render CMD z `CommandSchemaIR` |
| `app.doql.less` entities | **źródło nazw** schematów; LLM rozszerza, nie duplikuje ręcznie w Pythonie |
| Intract / PlanStepGate | kontrakt `input_model` ↔ IntentIR |

## SystemMapGenerator (LLM) — interfejs

```python
# docelowy moduł: nlp2dsl_sdk/system_map_generator.py

async def generate_system_map(
    *,
    example_id: str,
    hints: dict[str, Any],          # query, conversation state
    introspection: dict[str, Any],  # API snapshots, file listing
    llm_client: Any,
) -> SystemMapIR:
    """
    1. Build prompt with SystemMapIR JSON schema + introspection payload
    2. LLM returns JSON
    3. SystemMapIR.model_validate(json)
    4. Optionally emit dynamic Pydantic models via create_model()
    """
```

**Wejście introspection** (zamiast hardcode):

- `GET /workflow/actions/schema/{action}` — pełne JSON Schema
- listing Mullm / `fixtures/`
- `docker compose config` / profile `invoice`
- bieżący `ConversationState`

**Wyjście:** `SystemMapIR` → DOQL + bezpośrednio orchestrator (autofill, attachment gate).

## Stan migracji

| Komponent | Teraz | Cel |
|-----------|-------|-----|
| `collect_task_context()` | statyczny bootstrap | fallback offline |
| `build_runtimes_for_example()` | runtimes z example-profiles | + health, LLM |
| `command.runtime` | w DOQL / SystemMapIR | dispatch zamiast delegate if/else |
| `finalize()` | IR → DOQL via `render_system_map_doql` | + LLM gdy online |
| orchestrator | DOQL autofill | ProcessAgent ([`process-agent.md`](process-agent.md)) |

Zob. też: [`doql-runtimes.md`](doql-runtimes.md).

## Kolejność implementacji

1. **SystemMapIR** + render DOQL — ✅ `system_map_ir.py`, `system_map_render.py`
2. **SystemMapGenerator** — LLM prompt + validate (nlp-service lub SDK)
3. **Dynamic Pydantic** — `create_model` z `CommandSchemaIR.fields`
4. **Mapper refactor** — `validate_step_config` z mapy zamiast registry
5. **Usunięcie hardcode** — `load_platform_map`, `_command_transport` → introspection + IR
6. **Sync z app.doql.less** — generowanie encji DOQL z IR (SUMD/Propact pipeline)

Zob. [`doql-system-map.md`](doql-system-map.md) — rola pliku `environment.doql.less` jako widoku mapy.
