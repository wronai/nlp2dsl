"""Adapters between legacy action registries and ActionContract models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .action import ActionContract, CompatibilityContract, ExecutionContract

FIELD_TYPES: dict[str, str] = {
    "amount": "float",
    "to": "str",
    "currency": "str",
    "subject": "str",
    "body": "str",
    "report_type": "str",
    "format": "str",
    "entity": "str",
    "data": "dict",
    "channel": "str",
    "message": "str",
    "chat_id": "str",
    "webhook_url": "str",
    "attachment_path": "str",
    "output_path": "str",
    "setting_path": "str",
    "setting_value": "str",
    "section": "str",
    "file_path": "str",
    "content": "str",
    "directory": "str",
    "pattern": "str",
    "mode": "str",
    "action_name": "str",
    "action_description": "str",
    "required_fields": "list",
    "shell_command": "str",
    "description": "str",
    "language": "str",
    "context": "str",
    "include_tests": "bool",
    "title": "str",
}

SIDE_EFFECT_ACTIONS = frozenset(
    {
        "send_invoice",
        "generate_invoice",
        "send_email",
        "crm_update",
        "notify_slack",
        "notify_telegram",
        "notify_teams",
        "system_settings_set",
        "system_settings_reset",
        "system_file_write",
        "system_registry_add",
        "system_registry_edit",
        "mullm_shell_task",
        "mullm_create_ticket",
    }
)


def _optional_defaults(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list | tuple | set):
        return {str(k): None for k in raw}
    return {}


def _string_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, Mapping):
        return [str(k) for k in raw.keys()]
    try:
        return [str(v) for v in raw]
    except TypeError:
        return []


def _string_dict(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _execution_contract(name: str, meta: Mapping[str, Any]) -> ExecutionContract:
    category = str(meta.get("category") or "business")
    raw_execution = str(meta.get("execution") or meta.get("execution_mode") or "direct")
    backend = str(meta.get("execution_backend") or "")
    if not backend:
        if raw_execution == "delegate":
            backend = "delegate"
        elif category == "system":
            backend = "system"
        elif category == "mullm":
            backend = "mullm"
        else:
            backend = "worker"
    if backend not in {"worker", "system", "delegate", "mullm"}:
        backend = "unknown"
    side_effect = bool(meta.get("side_effect", name in SIDE_EFFECT_ACTIONS))
    idempotency = str(meta.get("idempotency") or ("required" if side_effect else "none"))
    if idempotency not in {"none", "optional", "required"}:
        idempotency = "optional"
    return ExecutionContract(
        backend=backend,  # type: ignore[arg-type]
        mode=raw_execution,
        side_effect=side_effect,
        idempotency=idempotency,  # type: ignore[arg-type]
        approval_required=bool(meta.get("approval_required", False)),
    )


def _compatibility_contract(meta: Mapping[str, Any]) -> CompatibilityContract:
    compatibility = str(meta.get("compatibility") or "backward")
    if compatibility not in {"backward", "forward", "breaking", "unknown"}:
        compatibility = "unknown"
    return CompatibilityContract(
        contract_version=int(meta.get("contract_version") or meta.get("version") or 1),
        executor_version=str(meta.get("executor_version") or "1"),
        event_version=int(meta.get("event_version") or 1),
        compatibility=compatibility,  # type: ignore[arg-type]
        migrations=_string_list(meta.get("migrations")),
    )


def contract_from_registry_entry(name: str, meta: Mapping[str, Any] | None) -> ActionContract:
    """Build an ActionContract from the legacy nlp-service ACTIONS_REGISTRY entry."""
    raw = dict(meta or {})
    version = int(raw.get("contract_version") or raw.get("version") or 1)
    category = str(raw.get("category") or "business")
    return ActionContract(
        name=name,
        version=version,
        description=str(raw.get("description") or name),
        category=category,
        required=_string_list(raw.get("required")),
        optional=_optional_defaults(raw.get("optional")),
        quality_required=_string_list(raw.get("quality_required")),
        aliases=_string_list(raw.get("aliases")),
        param_aliases=_string_dict(raw.get("param_aliases")),
        input_model=raw.get("input_model"),
        resource_area=raw.get("resource_area"),
        permission_action=str(raw.get("permission_action") or "execute"),
        capabilities=dict(raw.get("capabilities") or {}),
        execution=_execution_contract(name, raw),
        compatibility=_compatibility_contract(raw),
    )


def contract_from_catalog_entry(name: str, meta: Mapping[str, Any] | None) -> ActionContract:
    """Build an ActionContract from `/nlp/actions` payload."""
    return contract_from_registry_entry(name, meta)


def action_contracts_from_registry(
    registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, ActionContract]:
    return {
        name: contract_from_registry_entry(name, meta)
        for name, meta in sorted(registry.items())
        if isinstance(meta, Mapping)
    }


def action_contracts_from_catalog(
    catalog: Mapping[str, Any],
) -> dict[str, ActionContract]:
    return {
        name: contract_from_catalog_entry(name, meta if isinstance(meta, Mapping) else {})
        for name, meta in sorted(catalog.items())
    }


def action_catalog_payload(
    contracts: Mapping[str, ActionContract],
) -> dict[str, dict[str, Any]]:
    return {name: contract.to_catalog_entry() for name, contract in sorted(contracts.items())}


def action_info_config_schema(contract: ActionContract) -> dict[str, str]:
    schema: dict[str, str] = {}
    for field in contract.all_fields:
        schema[field] = FIELD_TYPES.get(field, "str")
    return schema


def required_fields_for_action(
    action: str,
    *,
    catalog: Mapping[str, Any],
) -> list[str]:
    contract = action_contracts_from_catalog(catalog).get(action)
    return list(contract.required) if contract else []


def quality_fields_for_action(
    action: str,
    *,
    catalog: Mapping[str, Any],
) -> list[str]:
    contract = action_contracts_from_catalog(catalog).get(action)
    return list(contract.quality_required) if contract else []


def known_action_names(*, catalog: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(str(name) for name in catalog.keys())
