"""
Mapper NLP → DSL — w pełni deterministyczny.

Zasada:
  LLM rozumie → Mapper buduje → Docker wykonuje

LLM NIGDY nie generuje finalnego DSL.
Mapper gwarantuje: przewidywalność, debugowalność, kontrolę.
"""

from __future__ import annotations

import logging

from .schemas import NLPResult, NLPEntities, WorkflowDSL, DSLStep, DialogResponse
from .registry import (
    ACTIONS_REGISTRY,
    COMPOSITE_INTENTS,
    get_required_fields,
    get_defaults,
    get_trigger,
)

log = logging.getLogger("nlp.mapper")


# ── Public API ────────────────────────────────────────────────


def map_to_dsl(nlp: NLPResult) -> DialogResponse:
    """
    Konwertuje NLPResult → WorkflowDSL.
    Jeśli brakuje wymaganych pól — zwraca DialogResponse z pytaniem.
    """
    intent = nlp.intent.intent
    entities = nlp.entities

    # Resolve actions from intent
    actions = _resolve_actions(intent)

    if not actions:
        return DialogResponse(
            status="error",
            prompt_user=(
                f"Nie rozpoznano intencji '{intent}'. "
                f"Dostępne akcje: {', '.join(ACTIONS_REGISTRY.keys())}"
            ),
        )

    # Build steps + collect missing fields
    steps: list[DSLStep] = []
    all_missing: list[str] = []

    for action_name in actions:
        config, missing = _build_config(action_name, entities)

        if missing:
            all_missing.extend(f"{action_name}.{f}" for f in missing)
        else:
            steps.append(DSLStep(action=action_name, config=config))

    # Detect trigger
    trigger = get_trigger(nlp.raw_text) if nlp.raw_text else "manual"

    # Generate workflow name
    name = _make_name(intent, actions)

    if all_missing:
        # Return partial workflow + missing fields
        return DialogResponse(
            status="incomplete",
            workflow=WorkflowDSL(name=name, trigger=trigger, steps=steps) if steps else None,
            missing_fields=all_missing,
            prompt_user=_build_prompt(all_missing),
        )

    workflow = WorkflowDSL(name=name, trigger=trigger, steps=steps)

    log.info("✔ DSL built: %s (%d steps, trigger=%s)", name, len(steps), trigger)
    return DialogResponse(status="complete", workflow=workflow)


# ── Internal ──────────────────────────────────────────────────


def _resolve_actions(intent: str) -> list[str]:
    """Resolve intent → list of action names."""
    # Direct action match
    if intent in ACTIONS_REGISTRY:
        return [intent]

    # Composite intent
    if intent in COMPOSITE_INTENTS:
        return list(COMPOSITE_INTENTS[intent])

    # Dynamic composite (e.g. "send_invoice_and_notify_slack")
    if "_and_" in intent:
        parts = intent.split("_and_")
        resolved = []
        for part in parts:
            part = part.strip()
            if part in ACTIONS_REGISTRY:
                resolved.append(part)
        if resolved:
            return resolved

    return []


def _build_config(action: str, entities: NLPEntities) -> tuple[dict, list[str]]:
    """Build config dict for action from entities. Returns (config, missing_fields)."""
    required = get_required_fields(action)
    defaults = get_defaults(action)
    entities_dict = entities.model_dump(exclude_none=True)

    config = {}
    missing = []

    # Map entity fields to config
    field_mapping = _get_field_mapping(action)

    for field in required:
        # Try direct match
        value = entities_dict.get(field)

        # Try mapped name
        if value is None:
            mapped_field = field_mapping.get(field, field)
            value = entities_dict.get(mapped_field)

        if value is None:
            missing.append(field)
        else:
            config[field] = value

    # Add optional fields with defaults
    for field, default in defaults.items():
        value = entities_dict.get(field)
        config[field] = value if value is not None else default

    return config, missing


def _get_field_mapping(action: str) -> dict[str, str]:
    """Standard field mappings per action."""
    mappings = {
        "send_invoice": {"to": "to", "amount": "amount", "currency": "currency"},
        "send_email": {"to": "to", "subject": "subject", "body": "message"},
        "generate_report": {"report_type": "report_type", "format": "format"},
        "crm_update": {"entity": "entity", "data": "data"},
        "notify_slack": {"channel": "channel", "message": "message"},
    }
    return mappings.get(action, {})


def _make_name(intent: str, actions: list[str]) -> str:
    """Generate a workflow name."""
    if intent in COMPOSITE_INTENTS:
        return intent
    if len(actions) == 1:
        return f"auto_{actions[0]}"
    return "auto_" + "_and_".join(actions)


def _build_prompt(missing: list[str]) -> str:
    """Build a user-facing prompt for missing fields."""
    field_descriptions = {
        "amount": "kwotę",
        "to": "adres e-mail odbiorcy",
        "currency": "walutę",
        "subject": "temat wiadomości",
        "report_type": "typ raportu (np. sales, hr, finance)",
        "format": "format (pdf, csv)",
        "channel": "kanał Slack (np. #general)",
        "message": "treść wiadomości",
        "entity": "typ encji CRM (np. contact, client)",
    }

    parts = []
    for field_ref in missing:
        # field_ref format: "action.field"
        field = field_ref.split(".")[-1]
        desc = field_descriptions.get(field, field)
        parts.append(desc)

    unique_parts = list(dict.fromkeys(parts))  # deduplicate preserving order
    return f"Podaj: {', '.join(unique_parts)}"
