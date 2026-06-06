# dsl-validate

Structured validation pipeline for NLP2DSL workflows: step config, DSL contracts, profile checks, capability policy, attachment PDF, runtime health.

## Dependencies

- `dsl-contracts` (`ValidationIssue` lives in `dsl_contracts.issue`, re-exported here)
- `env2llm` (`SystemMapIR`, profile validations)

## Usage

```python
from dsl_validate import (
    ValidationIssue,
    ValidationContext,
    validate_step_issues,
    validate_dsl_contract_issues,
    run_profile_validation_checks,
)
from dsl_contracts.issue import Phase

issues = validate_dsl_contract_issues(dsl, known_actions={"send_invoice", "send_email"})
```

Consumed by `backend`, `worker`, `nlp-service` via `nlp2dsl_sdk.validation` shims.

See [`docs/validation.md`](../../docs/validation.md).
