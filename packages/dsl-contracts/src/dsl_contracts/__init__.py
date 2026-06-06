"""Action contracts shared by nlp-service, backend, worker and SDK tools."""

from .action import (
    ActionContract,
    CompatibilityContract,
    ExecutionContract,
    FieldContract,
)
from .registry import (
    SIDE_EFFECT_ACTIONS,
    action_catalog_payload,
    action_contracts_from_catalog,
    action_contracts_from_registry,
    action_info_config_schema,
    contract_from_catalog_entry,
    contract_from_registry_entry,
    known_action_names,
    quality_fields_for_action,
    required_fields_for_action,
)

_DRAFT_EXPORTS = {
    "ContractDraft",
    "active_draft_contracts",
    "draft_ready_for_activation",
    "draft_path",
    "drafts_dir",
    "list_draft_files",
    "load_draft",
    "load_drafts",
    "save_draft",
    "validate_draft",
}


def __getattr__(name: str):
    if name in _DRAFT_EXPORTS:
        from . import draft

        return getattr(draft, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ActionContract",
    "CompatibilityContract",
    "ContractDraft",
    "ExecutionContract",
    "FieldContract",
    "SIDE_EFFECT_ACTIONS",
    "active_draft_contracts",
    "draft_ready_for_activation",
    "draft_path",
    "drafts_dir",
    "list_draft_files",
    "load_draft",
    "load_drafts",
    "save_draft",
    "validate_draft",
    "action_catalog_payload",
    "action_contracts_from_catalog",
    "action_contracts_from_registry",
    "action_info_config_schema",
    "contract_from_catalog_entry",
    "contract_from_registry_entry",
    "known_action_names",
    "quality_fields_for_action",
    "required_fields_for_action",
]
