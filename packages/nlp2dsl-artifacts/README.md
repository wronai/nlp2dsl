# nlp2dsl-artifacts

Write transparent example run artifacts under `examples/*/.nlp2dsl/`:

| File | Format |
|------|--------|
| `manifest.yaml` | `nlp2dsl.example_manifest.v1` |
| `pipeline/{slug}.json` | full workflow API response |
| `process/{slug}.process.yaml` | `nlp2dsl.process.v1` (NLP→DSL→CMD→process) |
| `commands.testql.toon.yaml` | generated TestQL commands |
| `services.yaml` | action catalog snapshot |

## Dependencies

- `env2llm` (environment map + registry layout)

## Usage

```python
from nlp2dsl_artifacts import ExampleArtifactWriter, build_process_trace

writer = ExampleArtifactWriter("examples/01-invoice", title="Invoice demo")
writer.record("Wyślij fakturę 1500 PLN", workflow_result)
writer.finalize(client)

trace = build_process_trace("query", result)
```

Shim: `nlp2dsl_sdk.artifacts`. See [`docs/artifacts.md`](../../docs/artifacts.md).
