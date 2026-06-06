"""
Autonomous resolution loop — validate → acquire/generate missing data → retry.

Runs inside one conversation turn when DOQL conversation.autofill is enabled.
Only asks the user when autonomous strategies are exhausted.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.conversation.invoice_policy import invoice_attachment_policy_active
from app.conversation.doql_autofill import (
    load_context_for_state,
    sync_autofill_from_doql,
    _nested_generate_invoice,
    _resolve_attachment_path,
)
from app.conversation.doql_context import DoqlTaskContext, autofill_entities, resolve_doql_context_path
from app.conversation.doql_registry import refresh_registry_for_state, reload_context_after_refresh
from app.conversation.responses import _nlp_from_state, build_and_check_dsl, build_incomplete_response
from app.conversation.system_map import set_doql_context
from app.dsl.pipeline import map_to_dsl_with_enrichment
from app.schemas import ConversationResponse, ConversationState, DialogResponse
from app.validation.step_validator import validate_step_config, validate_step_config_issues, validate_workflow_steps
from nlp2dsl_sdk.validation.resolutions import (
    ResolutionEnvironment,
    apply_resolution_plans,
    filter_plans_by_reflection_tokens,
    plan_resolutions,
)

log = logging.getLogger("orchestrator.autonomous")

_MAX_AUTONOMOUS_ROUNDS = 8


@dataclass
class AutonomousResolveResult:
    response: ConversationResponse | None = None
    steps: list[str] = field(default_factory=list)
    exhausted: bool = False


def _max_autonomous_rounds(ctx: DoqlTaskContext | None) -> int:
    if ctx is None:
        return _MAX_AUTONOMOUS_ROUNDS
    return int(ctx.process.autonomous_max_rounds or _MAX_AUTONOMOUS_ROUNDS)


def _autonomous_enabled(ctx: DoqlTaskContext | None) -> bool:
    if ctx is None:
        return False
    return bool(ctx.autofill and ctx.process.autonomous_enabled)


def _example_dir() -> Path | None:
    from app.request_context import get_example_dir

    req = get_example_dir()
    if req:
        return req
    raw = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    return Path(raw).resolve() if raw else None


def _step_config_for_validation(state: ConversationState) -> tuple[str, dict[str, Any]]:
    intent = state.intent or "send_invoice"
    config: dict[str, Any] = dict(state.entities)
    if state.dsl and state.dsl.steps:
        config = dict(state.dsl.steps[0].config)
    return intent, config


def _attachment_valid_ok(raw: str, ctx: DoqlTaskContext, state: ConversationState) -> bool:
    resolved = _resolve_artifact_file(raw, ctx)
    if resolved is None or not Path(resolved).is_file():
        return False
    intent, current = _step_config_for_validation(state)
    config: dict[str, Any] = dict(current)
    config["attachment_path"] = resolved
    for key in ("amount", "to", "currency"):
        if key not in config and key in state.entities:
            config[key] = state.entities[key]
    issues = validate_step_config(intent, config)
    return not any("attachment_path" in issue for issue in issues)


def _maybe_delete_generated_attachment(raw: str, ctx: DoqlTaskContext) -> None:
    resolved = _resolve_artifact_file(raw, ctx)
    if not resolved:
        return
    path = Path(resolved)
    markers = (".nlp2dsl/generated", "/tmp/nlp2dsl-invoices", "nlp2dsl-invoices")
    if any(marker in str(path) for marker in markers):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _resolve_artifact_file(raw: str, ctx: DoqlTaskContext) -> str | None:
    """Resolve DOQL artifact path to absolute existing file."""
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return str(path.resolve())

    ex = _example_dir()
    if ex:
        for candidate in (
            ex / raw,
            ex / "fixtures" / Path(raw).name,
            ex / ".nlp2dsl" / raw,
        ):
            if candidate.is_file():
                return str(candidate.resolve())

    doql_path = ctx.data.get("_doql_path")  # unused; use resolve via autofill module
    resolved = _resolve_attachment_path(raw, ctx)
    return resolved if Path(resolved).is_file() else None


def _try_fixture_attachment(state: ConversationState, ctx: DoqlTaskContext) -> str | None:
    if not invoice_attachment_policy_active(ctx, state):
        return None
    current = str(state.entities.get("attachment_path", "")).strip()
    if current and _attachment_valid_ok(current, ctx, state):
        return None
    if current:
        state.entities.pop("attachment_path", None)

    for art in ctx.artifacts:
        if not art.path:
            continue
        if art.path.lower().endswith((".pdf", ".txt")) or art.kind == "file":
            resolved = _resolve_artifact_file(art.path, ctx)
            if resolved:
                state.entities["attachment_path"] = resolved
                if _attachment_valid_ok(resolved, ctx, state):
                    return f"attachment_path ← artifact:{art.path}"
                state.entities.pop("attachment_path", None)

    ex = _example_dir()
    if ex:
        fixtures = ex / "fixtures"
        if fixtures.is_dir():
            for pattern in ("*.pdf", "*.PDF"):
                for path in sorted(fixtures.glob(pattern)):
                    state.entities["attachment_path"] = str(path.resolve())
                    if _attachment_valid_ok(str(path), ctx, state):
                        return f"attachment_path ← fixtures/{path.name}"
                    state.entities.pop("attachment_path", None)

    return None


def _try_generate_attachment(state: ConversationState, ctx: DoqlTaskContext) -> str | None:
    current = str(state.entities.get("attachment_path", "")).strip()
    if current and _attachment_valid_ok(current, ctx, state):
        return None
    if current:
        state.entities.pop("attachment_path", None)
    if not ctx.generate_invoice_if_missing:
        return None
    if not invoice_attachment_policy_active(ctx, state):
        return None
    caps_ok = "generate_invoice" in ctx.capabilities or not ctx.capabilities
    if not caps_ok:
        return None

    generated = _nested_generate_invoice(state, ctx)
    if not generated:
        return None
    state.entities["attachment_path"] = _resolve_attachment_path(generated, ctx)
    return "attachment_path (nested generate_invoice)"


async def _dialog_missing(state: ConversationState) -> list[str]:
    dialog = await map_to_dsl_with_enrichment(_nlp_from_state(state))
    if dialog.status == "complete":
        return []
    return list(dialog.missing_fields or [])


async def _try_validation_fixes(state: ConversationState, ctx: DoqlTaskContext) -> list[str]:
    """Fix validation errors via issue → resolution plans, guided by reflection tokens."""
    from app.conversation.reflection import reflection_from_state

    intent, config = _step_config_for_validation(state)
    issues = validate_step_config_issues(intent, config)
    if not issues:
        return []

    attachment_related = any(
        i.field_name == "attachment_path" or i.code.startswith("attachment.") for i in issues
    )
    if attachment_related and not invoice_attachment_policy_active(ctx, state):
        return []

    def _clear_field(field: str) -> None:
        state.entities.pop(field, None)
        if state.dsl and state.dsl.steps:
            state.dsl.steps[0].config.pop(field, None)

    def _try_autofill(issue) -> str | None:
        field = issue.field_name
        if not field:
            return None
        ref = f"{intent}.{field}" if "." not in field else field
        updated, filled = autofill_entities(state.entities, [ref], ctx, intent=intent)
        if filled:
            state.entities.update(updated)
            if state.dsl and state.dsl.steps:
                state.dsl.steps[0].config.update({k: updated[k] for k in filled if k in updated})
            return filled[0]
        return None

    env = ResolutionEnvironment(
        clear_field=_clear_field,
        delete_generated_attachment=lambda raw: _maybe_delete_generated_attachment(raw, ctx),
        get_attachment_path=lambda: str(
            (state.dsl.steps[0].config.get("attachment_path") if state.dsl and state.dsl.steps else None)
            or state.entities.get("attachment_path", "")
        ).strip(),
        pick_fixture=lambda: _try_fixture_attachment(state, ctx),
        generate=lambda _hint: _try_generate_attachment(state, ctx),
        autofill=_try_autofill,
    )

    reflection = reflection_from_state(state, "autonomous_validate")
    tokens = reflection.get("resolutions_available") or []
    plans = plan_resolutions(issues)
    plans = filter_plans_by_reflection_tokens(plans, tokens)
    return apply_resolution_plans(plans, env)


async def autonomous_resolve_turn(state: ConversationState) -> AutonomousResolveResult:
    """
    Loop: autofill → fixtures → generate → DSL → validate until ready or stuck.
    Returns ready ConversationResponse when autonomous path succeeds.
    """
    ctx = load_context_for_state(state)
    if not _autonomous_enabled(ctx):
        return AutonomousResolveResult()

    set_doql_context(ctx)
    steps: list[str] = list(state.autonomous_steps or [])
    max_rounds = _max_autonomous_rounds(ctx)

    for round_idx in range(max_rounds):
        progress = False
        log.info("Autonomous round %d/%d intent=%s", round_idx + 1, max_rounds, state.intent)

        applied = await sync_autofill_from_doql(state)
        if applied:
            steps.extend(applied)
            progress = True

        fixture = _try_fixture_attachment(state, ctx)
        if fixture:
            steps.append(fixture)
            progress = True

        generated = _try_generate_attachment(state, ctx)
        if generated:
            steps.append(generated)
            progress = True

        missing = await _dialog_missing(state)
        if missing:
            state.missing = missing
            updated, filled = autofill_entities(
                state.entities, missing, ctx, intent=state.intent
            )
            if filled:
                state.entities.update(updated)
                steps.extend(filled)
                progress = True

        refresh_registry_for_state(state, phase=f"autonomous_{round_idx + 1}")
        reload_context_after_refresh(state)
        ctx = load_context_for_state(state)
        if ctx:
            set_doql_context(ctx)

        ready_resp = await build_and_check_dsl(state)
        if ready_resp and ready_resp.status == "ready":
            validation = validate_workflow_steps(state.dsl.steps) if state.dsl else []
            if not validation:
                steps = list(dict.fromkeys(steps))
                state.autonomous_steps = steps
                state.autofill_applied = list(dict.fromkeys(state.autofill_applied + steps))
                msg = ready_resp.message or ""
                if steps:
                    msg += f"\n(Autonomicznie: {', '.join(steps)})"
                    ready_resp.message = msg
                ready_resp.autonomous_steps = steps
                log.info("Autonomous ready after %d rounds: %s", round_idx + 1, steps)
                return AutonomousResolveResult(response=ready_resp, steps=steps)

        fixes = await _try_validation_fixes(state, ctx)
        if fixes:
            steps.extend(fixes)
            progress = True
            continue

        if ready_resp and ready_resp.status == "in_progress":
            # validation still failing — one more generate/fix cycle
            if not progress:
                break
            continue

        if not progress:
            break

    steps = list(dict.fromkeys(steps))
    state.autonomous_steps = steps
    return AutonomousResolveResult(steps=steps, exhausted=True)
