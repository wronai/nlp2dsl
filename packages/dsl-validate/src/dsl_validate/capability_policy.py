"""Capability and execution policy checks before side effects run."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from dsl_contracts.issue import Phase, ValidationIssue
from dsl_contracts.registry import action_contracts_from_catalog
from env2llm.ir import ProcessPolicyIR
from env2llm.policy.process import process_scope_denied

_EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+)$")


@dataclass
class ExecutionPolicyContext:
    """Runtime policy envelope applied at pre-execute."""

    agent_id: str = "user"
    executing: bool = True
    dry_run_only: bool = False
    approval_grants: frozenset[str] = field(default_factory=frozenset)
    approval_token: str | None = None
    allowed_email_domains: frozenset[str] = field(default_factory=frozenset)
    allowed_notify_channels: frozenset[str] = field(default_factory=frozenset)
    process: ProcessPolicyIR | None = None
    access_decisions: dict[str, Mapping[str, Any]] = field(default_factory=dict)


def _workflow_steps(workflow: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [s for s in (workflow.get("steps") or []) if isinstance(s, Mapping)]


def _step_config(step: Mapping[str, Any]) -> dict[str, Any]:
    raw = step.get("config") or step.get("parameters") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _email_domain(address: str) -> str | None:
    match = _EMAIL_RE.match(str(address or "").strip())
    return match.group(1).lower() if match else None


def _target_uri(action: str, config: Mapping[str, Any]) -> str | None:
    if action in {"send_email", "send_invoice", "generate_invoice"}:
        recipient = str(config.get("to") or "").strip()
        return f"mailto:{recipient}" if recipient else None
    webhook = str(config.get("webhook_url") or "").strip()
    if webhook:
        return webhook
    return None


def _approval_granted(
    action: str,
    config: Mapping[str, Any],
    ctx: ExecutionPolicyContext,
) -> bool:
    if action in ctx.approval_grants:
        return True
    step_token = str(config.get("approval_token") or "").strip()
    if ctx.approval_token and step_token and step_token == ctx.approval_token:
        return True
    if ctx.approval_token and not step_token and action in ctx.approval_grants:
        return True
    return False


def validate_capability_policy(
    workflow: Mapping[str, Any],
    catalog: Mapping[str, Any],
    ctx: ExecutionPolicyContext,
    *,
    phase: Phase = Phase.PRE_EXECUTE,
) -> list[ValidationIssue]:
    """Return policy violations that must block execution before the worker."""
    contracts = action_contracts_from_catalog(catalog)
    issues: list[ValidationIssue] = []

    for index, step in enumerate(_workflow_steps(workflow)):
        action = str(step.get("action") or "")
        if not action:
            continue
        config = _step_config(step)
        contract = contracts.get(action)
        step_ref = f"steps.{index}"

        if ctx.process is not None:
            area = contract.resource_area if contract else None
            denied = process_scope_denied(ctx.process, action=action, resource_area=area)
            if denied:
                issues.append(
                    ValidationIssue(
                        code="policy.scope_denied",
                        field_name=step_ref,
                        message=denied,
                        phase=phase,
                        kind="blocked",
                        resolution="blocked",
                        meta={"action": action, "resource_area": area},
                    )
                )
                continue

        if not contract:
            continue

        side_effect = bool(contract.execution.side_effect)
        if ctx.dry_run_only and ctx.executing and side_effect:
            issues.append(
                ValidationIssue(
                    code="policy.dry_run_only",
                    field_name=step_ref,
                    message=(
                        f"Akcja `{action}` ma efekt uboczny — tryb dry_run_only blokuje wykonanie."
                    ),
                    phase=phase,
                    kind="blocked",
                    resolution="blocked",
                    meta={"action": action},
                )
            )
            continue

        if ctx.executing and contract.execution.approval_required and not _approval_granted(
            action, config, ctx
        ):
            issues.append(
                ValidationIssue(
                    code="policy.approval_required",
                    field_name=step_ref,
                    message=(
                        f"Akcja `{action}` wymaga zatwierdzenia (approval_required). "
                        "Przekaż approval_grants lub approval_token."
                    ),
                    phase=phase,
                    kind="blocked",
                    resolution="blocked",
                    meta={"action": action},
                )
            )

        decision = ctx.access_decisions.get(action)
        if ctx.executing and decision and not decision.get("allowed"):
            effect = str(decision.get("effect") or "deny")
            if effect == "approval" and _approval_granted(action, config, ctx):
                pass
            else:
                reason = str(decision.get("reason") or effect)
                issues.append(
                    ValidationIssue(
                        code="policy.access_denied",
                        field_name=step_ref,
                        message=(
                            f"Agent `{ctx.agent_id}` nie może wykonać `{action}` "
                            f"(effect={effect}, reason={reason})."
                        ),
                        phase=phase,
                        kind="blocked",
                        resolution="blocked",
                        meta={
                            "action": action,
                            "agent_id": ctx.agent_id,
                            "effect": effect,
                            "reason": reason,
                        },
                    )
                )
                continue

        if ctx.executing and ctx.allowed_email_domains and action in {
            "send_email",
            "send_invoice",
            "generate_invoice",
        }:
            recipient = str(config.get("to") or "").strip()
            domain = _email_domain(recipient)
            if domain and domain not in ctx.allowed_email_domains:
                issues.append(
                    ValidationIssue(
                        code="policy.recipient_not_allowed",
                        field_name=f"{step_ref}.config.to",
                        message=(
                            f"Domena `{domain}` nie jest na liście dozwolonych odbiorców "
                            f"({', '.join(sorted(ctx.allowed_email_domains))})."
                        ),
                        phase=phase,
                        kind="blocked",
                        resolution="blocked",
                        meta={"action": action, "domain": domain},
                    )
                )

        if ctx.executing and ctx.allowed_notify_channels and action in {
            "notify_slack",
            "notify_teams",
            "notify_telegram",
        }:
            channel = str(
                config.get("channel") or config.get("chat_id") or ""
            ).strip()
            if channel and channel not in ctx.allowed_notify_channels:
                issues.append(
                    ValidationIssue(
                        code="policy.channel_not_allowed",
                        field_name=f"{step_ref}.config.channel",
                        message=(
                            f"Kanał `{channel}` nie jest dozwolony "
                            f"({', '.join(sorted(ctx.allowed_notify_channels))})."
                        ),
                        phase=phase,
                        kind="blocked",
                        resolution="blocked",
                        meta={"action": action, "channel": channel},
                    )
                )

    return issues


def access_decision_requires_approval(decision: Mapping[str, Any]) -> bool:
    return str(decision.get("effect") or "") == "approval" and not decision.get("allowed")


def build_access_decision_params(
    action: str,
    config: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
) -> dict[str, str]:
    """Query params for nlp-service GET /nlp/access/check."""
    contracts = action_contracts_from_catalog(catalog)
    contract = contracts.get(action)
    params: dict[str, str] = {
        "agent_id": "",
        "action": action,
        "permission_action": "execute",
    }
    if contract:
        params["permission_action"] = str(contract.permission_action or "execute")
        if contract.resource_area:
            params["resource_area"] = str(contract.resource_area)
    uri = _target_uri(action, config)
    if uri:
        params["uri"] = uri
    return params
