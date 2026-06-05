# Autonomiczny stack (compose + cron)

Przykład [`13-autonomous-invoice-stack`](../examples/13-autonomous-invoice-stack/) pokazuje pełny proces:

1. **Registry** — `environment.doql.less` jako live mapa (runtimes, commands, data, schedules, deploy)
2. **Autonomiczna pętla** — `autonomous_loop` + `ReflectionReport` (walidacja przed `ready`)
3. **Multi-turn** — złożone polecenia NL (faktura + harmonogram) z uzupełnianiem braków
4. **Generacja compose** — `nlp2dsl_sdk.compose_generator` emituje stack + cron
5. **Nowe usługi** — stub `generated_services[]` gdy brakuje sidecar runnera

## SDK

```python
from nlp2dsl_sdk.stack_flow import AutonomousStackFlow

flow = AutonomousStackFlow(client, example_dir="examples/13-autonomous-invoice-stack")
result = flow.run_phases()
print(result.compose.up_command)
```

```python
from nlp2dsl_sdk.compose_generator import generate_stack_compose
from nlp2dsl_sdk.system_map_bridge import doql_file_to_system_map

ir = doql_file_to_system_map(".nlp2dsl/registry/environment.doql.less")
gen = generate_stack_compose(ir, example_dir="examples/13-autonomous-invoice-stack")
```

## SystemMapIR — nowe pola

| Pole | Opis |
|------|------|
| `schedules[]` | `id`, `cron`, `task`, `workflow_action` |
| `deploy` | ścieżki compose, profile Docker, cron service |
| `generated_services[]` | stub Dockerfile pod `.nlp2dsl/generated/services/` |

Renderowane w DOQL jako bloki `schedules[]`, `deploy {}`, `generated_services[]`.

## Cron w Docker Compose

Generator tworzy usługę `invoice-stack-cron` (Ofelia) z profilem `autonomous-stack`:

- `ofelia.ini` — wpisy `[job-local]` per schedule
- `run-scheduled-task.sh` — `curl` do `POST /workflow/run` na backendzie
- mount `./examples:/examples:ro` na platformie (root `docker-compose.yml`)

## Ograniczenia MVP

| Aspekt | Stan |
|--------|------|
| Compose merge z platformą | dokumentowany `up_command` (3 pliki compose) |
| Health-check runtimes przed autofill | planowane |
| `generate_code` → rejestracja w ACTIONS_REGISTRY | planowane |
| Post-exec TestQL VALIDATE file | planowane |

Zob. też [`process-agent.md`](process-agent.md), [`doql-dynamic-generation.md`](doql-dynamic-generation.md).
