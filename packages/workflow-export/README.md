# workflow-export

Export validated workflow DSL and action contracts to **markpact** README bundles and **pactown** ecosystem manifests.

## Dependencies

- `dsl-contracts`

## Usage

```python
from pathlib import Path
from workflow_export import export_workflow_publish_layer, catalog_from_nlp_client

bundle = export_workflow_publish_layer(
    Path("examples/03-report-and-notify/.nlp2dsl"),
    dsl={"name": "report_and_email", "steps": [...]},
    catalog=catalog_from_nlp_client(client),
)
# → generated/markpact/README.md, generated/pactown/nlp2dsl-platform.pactown.yaml
```

Used by examples 03, 04, 14. Shim: `nlp2dsl_sdk.export`.
