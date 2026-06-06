"""
Mapper NLP → DSL — w pełni deterministyczny.

Zasada:
  LLM rozumie → Mapper buduje → Docker wykonuje

LLM NIGDY nie generuje finalnego DSL.
Mapper gwarantuje: przewidywalność, debugowalność, kontrolę.
"""

import logging

from app.registry import (
    COMPOSITE_INTENTS,
    get_defaults,
    get_quality_required_fields,
    get_required_fields,
    get_trigger,
)
from app.conversation.system_map import known_action_names
from app.schemas import DialogResponse, DSLStep, NLPEntities, NLPResult, WorkflowDSL

log = logging.getLogger("nlp.mapper")


# ── Public API ────────────────────────────────────────────────


def _unknown_intent_response(intent: str) -> DialogResponse:
    allowed = sorted(known_action_names())
    return DialogResponse(
        status="error",
        prompt_user=(
            f"Nie rozpoznano intencji '{intent}'. "
            f"Dostępne akcje: {', '.join(allowed)}"
        ),
    )


def _collect_workflow_steps(
    actions: list[str],
    entities: NLPEntities,
) -> tuple[list[DSLStep], list[str]]:
    steps: list[DSLStep] = []
    all_missing: list[str] = []
    for action_name in actions:
        config, missing = _build_config(action_name, entities)
        if missing:
            all_missing.extend(f"{action_name}.{f}" for f in missing)
        else:
            steps.append(DSLStep(action=action_name, config=config))
    return steps, all_missing


def map_to_dsl(nlp: NLPResult) -> DialogResponse:
    """
    Konwertuje NLPResult → WorkflowDSL.
    Jeśli brakuje wymaganych pól — zwraca DialogResponse z pytaniem.
    """
    intent = nlp.intent.intent
    actions = _resolve_actions(intent)
    if not actions:
        return _unknown_intent_response(intent)

    steps, all_missing = _collect_workflow_steps(actions, nlp.entities)
    trigger = get_trigger(nlp.raw_text) if nlp.raw_text else "manual"
    name = _make_name(intent, actions)

    if all_missing:
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
    allowed = known_action_names()

    if intent in allowed:
        return [intent]

    if intent in COMPOSITE_INTENTS:
        composite = [a for a in COMPOSITE_INTENTS[intent] if a in allowed]
        if composite:
            return composite

    if "_and_" in intent:
        parts = intent.split("_and_")
        resolved = []
        for part in parts:
            part = part.strip()
            if part in allowed:
                resolved.append(part)
        if resolved:
            return resolved

    return []


def _entity_value(field: str, entities_dict: dict, field_mapping: dict[str, str]):
    value = entities_dict.get(field)
    if value is None:
        value = entities_dict.get(field_mapping.get(field, field))
    return value


def _fill_required_config(
    action: str,
    entities_dict: dict,
    *,
    required: list[str],
    defaults: dict,
    field_mapping: dict[str, str],
) -> tuple[dict, list[str]]:
    config: dict = {}
    missing: list[str] = []
    for field in required:
        value = _entity_value(field, entities_dict, field_mapping)
        if value is None:
            missing.append(field)
        else:
            config[field] = value
    for field, default in defaults.items():
        value = _entity_value(field, entities_dict, field_mapping)
        config[field] = value if value is not None else default
    return config, missing


def _enrich_send_email_config(config: dict, entities_dict: dict) -> None:
    if entities_dict.get("email_to"):
        config["to"] = entities_dict["email_to"]
    if str(config.get("body", "")).strip():
        return
    report_type = entities_dict.get("report_type")
    if report_type:
        config["body"] = f"W załączeniu przesyłamy raport {report_type}."
    elif entities_dict.get("amount"):
        config["body"] = (
            f"Faktura na kwotę {entities_dict['amount']} "
            f"{entities_dict.get('currency', 'PLN')} została wystawiona."
        )


def _append_quality_missing(action: str, config: dict, missing: list[str]) -> None:
    for field in get_quality_required_fields(action):
        value = config.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)


def _build_config(action: str, entities: NLPEntities) -> tuple[dict, list[str]]:
    """Build config dict for action from entities. Returns (config, missing_fields)."""
    from app.conversation.system_map import required_fields_for_action

    required = required_fields_for_action(action) or get_required_fields(action)
    defaults = get_defaults(action)
    entities_dict = entities.model_dump(exclude_none=True)
    field_mapping = _get_field_mapping(action)

    config, missing = _fill_required_config(
        action,
        entities_dict,
        required=required,
        defaults=defaults,
        field_mapping=field_mapping,
    )

    if action == "send_email":
        _enrich_send_email_config(config, entities_dict)
    elif action.startswith("notify_") and not str(config.get("message", "")).strip():
        if auto_msg := _auto_notify_message(config, entities_dict):
            config["message"] = auto_msg

    _append_quality_missing(action, config, missing)

    if action == "send_invoice" and entities_dict.get("_doql_attachment_required"):
        if not str(config.get("attachment_path", "")).strip():
            missing.append("attachment_path")

    return config, missing


def _auto_notify_message(config: dict, entities_dict: dict) -> str | None:
    """Heuristic notify body when channel present but user gave no explicit text."""
    report_type = entities_dict.get("report_type")
    channel = config.get("channel") or entities_dict.get("channel")
    if report_type and channel:
        return f"📊 Raport {report_type} jest dostępny."
    amount = entities_dict.get("amount")
    if amount and channel:
        currency = entities_dict.get("currency", "PLN")
        return f"📄 Faktura {amount} {currency} — powiadomienie automatyczne."
    return None


def _get_field_mapping(action: str) -> dict[str, str]:
    """Standard field mappings per action."""
    mappings = {
        "send_invoice": {"to": "to", "amount": "amount", "currency": "currency", "attachment_path": "attachment_path"},
        "send_email": {"to": "to", "subject": "subject", "body": "message"},
        "generate_report": {"report_type": "report_type", "format": "format"},
        "generate_invoice": {"to": "to", "amount": "amount", "currency": "currency", "output_path": "output_path"},
        "crm_update": {"entity": "entity", "data": "data"},
        "notify_slack": {"channel": "channel", "message": "message"},
        "notify_telegram": {"chat_id": "chat_id", "message": "message"},
        "notify_teams": {"channel": "channel", "message": "message"},
        "generate_code": {
            "description": "description",
            "language": "language",
            "context": "context",
            "include_tests": "include_tests",
        },
    }
    return mappings.get(action, {})


def _make_name(intent: str, actions: list[str]) -> str:
    """Generate a workflow name."""
    if intent in COMPOSITE_INTENTS:
        return intent
    if len(actions) == 1:
        return f"auto_{actions[0]}"
    return f"auto_{'_and_'.join(actions)}"


def _build_prompt(missing: list[str]) -> str:
    """Build a user-facing prompt for missing fields."""
    field_descriptions = {
        "amount": "kwotę",
        "to": "adres e-mail odbiorcy",
        "currency": "walutę",
        "subject": "temat wiadomości",
        "body": "treść wiadomości (body)",
        "report_type": "typ raportu (np. sales, hr, finance)",
        "format": "format (pdf, csv)",
        "channel": "kanał Slack (np. #general)",
        "chat_id": "identyfikator czatu Telegram",
        "title": "tytuł powiadomienia",
        "message": "treść wiadomości",
        "entity": "typ encji CRM (np. contact, client)",
        "attachment_path": "nazwę pliku faktury (PDF)",
    }

    parts = []
    for field_ref in missing:
        # field_ref format: "action.field"
        field = field_ref.split(".")[-1]
        desc = field_descriptions.get(field, field)
        parts.append(desc)

    unique_parts = list(dict.fromkeys(parts))  # deduplicate preserving order
    return f"Podaj: {', '.join(unique_parts)}"
