# nlp2dsl-stack

Generate docker-compose stack, cron, and service Dockerfiles from `SystemMapIR`.

## Dependencies

- `env2llm` (semcod)

## Output (under `.nlp2dsl/generated/`)

- `docker-compose.stack.yaml`
- `crontab`, `run-scheduled-task.sh`, `up-stack.sh`
- `stack.manifest.yaml`
- `services/<name>/Dockerfile`

## Usage

```python
from pathlib import Path
from env2llm import generate_system_map
from nlp2dsl_stack import enrich_ir_for_stack, generate_stack_compose

ir = generate_system_map("examples/13-autonomous-invoice-stack")
ir = enrich_ir_for_stack(ir, example_id="13-autonomous-invoice-stack")
result = generate_stack_compose(Path("examples/13-autonomous-invoice-stack"), ir)
```

Shim: `nlp2dsl_sdk.compose_generator`. Multi-turn orchestration stays in `nlp2dsl_sdk.stack_flow`.
