# dsl-contracts

Canonical action contract models for NLP2DSL: `ActionContract`, registry adapters, and LLM-generated contract drafts.

## Install

```bash
pip install -e packages/dsl-contracts
# lub: ./packages/install-dev.sh
```

## Usage

```python
from dsl_contracts import (
    ActionContract,
    contract_from_registry_entry,
    action_catalog_payload,
    validate_draft,
    save_draft,
    ContractDraft,
)

contract = contract_from_registry_entry("send_invoice", {
    "required": ["amount", "to"],
    "optional": {"currency": "PLN"},
})
catalog = action_catalog_payload({"send_invoice": contract})
```

Drafty LLM trafiają do `.nlp2dsl/generated/contracts/*.draft.yaml`.

## Backward compatibility

`nlp2dsl_sdk.contracts` re-exports this package.
