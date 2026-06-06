# Plan refaktoryzacji nlp2dsl (integracja Mullm i rozszerzalność)

Plan wykonawczy 30/60/90, granice bounded contexts i docelowa struktura repo:
[`ROADMAP-30-60-90.md`](ROADMAP-30-60-90.md).

## Diagnoza (stan obecny)

| Problem | Skutek |
|---------|--------|
| **4 kopie rejestru akcji** (`registry.py`, `backend/workflow.py`, `worker.py`, runtime `system_executor`) | Nowa akcja = 3–4 pliki, dryf |
| **Chat tylko `parse_rules`** | Słabe rozpoznanie vs `/nlp/to-dsl` (auto/LLM) |
| **Wykonanie binarne** system → lokalnie, reszta → worker | Brak miejsca na Mullm / zewnętrzne backendy |
| **`main.py` ~500 linii** | Trudne testy i pluginy |
| **LLM prompt statyczny** | Nowe akcje (system, code, Mullm) niewidoczne dla LLM |
| **Duplikat schematów** backend ↔ nlp-service | Koszt utrzymania |

## Cel architektury docelowej

```
Tekst → parsing.facade (rules|llm|auto)
     → orchestrator (stan + formularz)
     → mapper → DSL
     → executors.router
           ├─ system (lokalnie)
           ├─ worker (HTTP)
           └─ mullm / inne (HTTP, env)
```

Zasada z README zostaje: **LLM rozumie → registry waliduje → mapper buduje → executor wykonuje**.

---

## Fazy

### Faza 1 — Fundament

- [x] `nlp2dsl.yaml` — resource_areas, agents, grants, native_routing (`app/access/`)
- [x] API `/nlp/access/config`, `/nlp/access/check`
- [x] Orchestrator: native route + ACL przed rules/LLM

### Faza 1b — wcześniejsze (integracje)

- [x] `nlp-service/integrations/loader.py` — pluginy z `INTEGRATIONS=mullm`
- [x] `nlp-service/integrations/mullm/registry.py` — akcje Mullm
- [x] `MULLM_ACTIONS` w `registry.py`
- [x] `app/parsing/facade.py` — jeden punkt parsowania
- [x] Orchestrator używa `parse_text(..., mode=os.getenv("NLP_CHAT_MODE","auto"))`
- [x] `NLPEntities` + `FIELD_TYPES` dla pól Mullm
- [x] Backend: przy `uruchom` nie wysyła kroków `mullm` do workera (`execution_backend: mullm`)

### Faza 2 — Porządek modułów (następny sprint)

- [x] Rozbić `nlp-service/app/main.py` na `routers/` (nlp, chat, schema, settings, system, code, ws)
- [x] `backend/routers/workflow.py` — proxy `/workflow/actions` → nlp-service `/nlp/actions`
- [x] `worker/registry.py` — walidacja handlerów vs katalog nlp-service przy starcie
- [x] `routing/parser/prompt_catalog.py` — `SYSTEM_PROMPT` z registry dynamicznie

### Faza 3 — Pakiet wspólny

- `packages/contract/` — `ActionMeta`, schematy DSL/NLP współdzielone z SDK
- Editable install w Dockerfile backend + nlp-service + worker

### Faza 4 — Executor Mullm w nlp2dsl

- `integrations/mullm/client.py` — `POST {MULLM_API}/api/...` (ticket, shell)
- `executors/router.py` w nlp-service dla akcji system+mullm
- Opcjonalnie: backend auto-wykonuje Mullm bez pośrednictwa web BFF

---

## Konwencja akcji zewnętrznych

```python
{
  "mullm_shell_task": {
    "category": "mullm",      # nie "system", nie business-worker
    "required": ["shell_command"],
    "execution": "delegate",  # opcjonalnie w meta
    ...
  }
}
```

Kategorie: `business` | `system` | `mullm` | (przyszłe: `koru`, …)

---

## Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `INTEGRATIONS` | `mullm` | Lista pluginów (comma-separated) |
| `NLP_CHAT_MODE` | `auto` | Tryb parsera w rozmowie |
| `MULLM_API_URL` | — | Backend Mullm (Faza 4) |

---

## Sync z repo Mullm

- Źródło prawdy akcji Mullm: `mullm/integrations/nlp2dsl/mullm_registry.py`
- Kopia / sync: `nlp2dsl/nlp-service/integrations/mullm/registry.py`
- Skrypt (opcjonalnie): `scripts/sync-mullm-registry.sh`

Mullm `conductor.py` może zostać cienkim klientem HTTP — logika dialogu w nlp2dsl.

---

## Faza 5 — Modułowa walidacja requestu

**Cel:** jeden silnik walidacji dla całego requestu (preflight → post-exec), reguły ze struktury DOQL/SystemMapIR, autonomiczna naprawa bez duplikacji.

### Diagnoza (code2llm / stan 2026-06)

| Problem | Skutek |
|---------|--------|
| 3–4 kopie `step_validator` / `attachment_validation` | Drift reguł (strict PDF tylko w nlp-service) |
| 3 źródła schematu (registry, DoqlTaskContext, SystemMapIR) | Niespójne required fields |
| Reflection parsuje polskie stringi z validatorów | Kruche API |
| `doql_context.py` GOD (~779L) | Trudna rozbudowa |
| `example-profiles.validations` tylko w E2E | Brak runtime hooków |

### Docelowa struktura

```
nlp2dsl_sdk/
  doql/              # split doql_context.py
  validation/        # ValidationIssue, Pipeline, rules/
  reflection/        # operuje na ValidationIssue.code
```

nlp-service / backend / worker → cienkie adaptery importujące SDK.

### Etapy (PR-y inkrementalne)

| Etap | Zadanie | Status |
|------|---------|--------|
| A0 | `ValidationIssue` + kody błędów | ✅ `nlp2dsl_sdk/validation/issue.py` |
| A1 | `validation/pipeline.py` + reguły step/attachment | ✅ SDK + adaptery nlp-service/backend |
| A2 | Split `doql_context.py` → `doql/models.py` | ✅ `doql/{models,parse,render,runtime}.py` + shim |
| B1 | backend/worker na pipeline SDK | ✅ backend + worker step_validator / attachment_validation |
| B2 | Fazy `post_execute`, `post_health` | ✅ pipeline entry points + backend/runtime_gate |
| C1 | DOQL commands zamiast ACTIONS_REGISTRY | ✅ backend step_validator + `/workflow/actions` → `/nlp/actions`; worker drift check |
| C2 | nlp-service usuwa duplikat doql_context | ✅ shim + SDK runtime helpers; `validations[]` parse roundtrip |
| C3 | `example-profiles.validations` → kody runtime | ✅ ProfileValidationIR + profile_checks + render/apply |

Docker: `build.context: .` — obrazy nlp-service/backend kopiują `nlp2dsl_sdk/`.

### Metryki sukcesu

- Zero duplikatów `path_resolve`, `invoice_pdf`, `attachment_validation`
- Reflection na `issue.code`, nie stringach
- Walidacja w 4 fazach z jednego pipeline
- `doql_context.py` → shim re-export (<50L)

Szczegóły: [`validation.md`](validation.md)

### Powiązane pliki (dziś)

| Warstwa | Plik |
|---------|------|
| nlp-service | `app/validation/step_validator.py`, `attachment_validation.py`, `path_policy.py` |
| nlp-service | `app/conversation/autonomous_loop.py`, `runtime_gate.py` |
| backend | `app/step_validator.py`, `attachment_validation.py` |
| SDK | `step_validation.py`, `attachment_validation.py`, `reflection.py`, `invoice_pdf.py` |
| worker | `path_resolve.py`, `step_validator.py`, `attachment_validation.py`, `registry.py` |
