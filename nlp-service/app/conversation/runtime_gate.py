"""Preflight: verify command runtime is available before autofill/execute."""

from __future__ import annotations

from app.conversation.doql_context import DoqlTaskContext

_WORKER_ACTIONS = frozenset(
    {
        "send_invoice",
        "generate_invoice",
        "send_email",
        "generate_report",
        "crm_update",
        "notify_slack",
        "notify_telegram",
        "notify_teams",
        "generate_code",
    }
)


def _runtime_id_for_intent(intent: str | None) -> str | None:
    if not intent:
        return None
    if intent.startswith("mullm_"):
        return "delegate:mullm"
    if intent.startswith("system_"):
        return "orchestrator:nlp-service"
    if intent in _WORKER_ACTIONS:
        return "executor:worker"
    return None


def runtime_unavailable_message(ctx: DoqlTaskContext, intent: str | None) -> str | None:
    """
    Return user-facing message when DOQL map lists runtime as unavailable.
    None when OK or map has no runtimes section (legacy DOQL).
    """
    runtime_id = _runtime_id_for_intent(intent)
    if not runtime_id or not ctx.runtimes:
        return None
    by_id = {r.id: r for r in ctx.runtimes}
    rt = by_id.get(runtime_id)
    if rt is None:
        return None
    if rt.status == "unavailable":
        return (
            f"Środowisko wykonania `{runtime_id}` jest niedostępne w tym przykładzie. "
            "Sprawdź profile Docker lub mapę runtimes w environment.doql.less."
        )
    return None
