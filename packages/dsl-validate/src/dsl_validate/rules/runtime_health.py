"""Runtime health validation — POST_HEALTH phase (DOQL runtimes[])."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Sequence

from ..issue import Phase, ValidationIssue

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


def runtime_id_for_intent(intent: str | None) -> str | None:
    if not intent:
        return None
    if intent.startswith("mullm_"):
        return "delegate:mullm"
    if intent.startswith("system_"):
        return "orchestrator:nlp-service"
    if intent in _WORKER_ACTIONS:
        return "executor:worker"
    return None


def probe_health_endpoint(url: str, *, timeout_s: float = 2.0) -> bool:
    """GET health URL; accept 200 with JSON status ok/healthy when present."""
    if not url.strip():
        return True
    try:
        req = urllib.request.Request(url.strip(), headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            if resp.status != 200:
                return False
            body = resp.read(4096)
            if not body:
                return True
            try:
                payload = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return True
            if isinstance(payload, dict):
                status = str(payload.get("status", "")).lower()
                if status in ("ok", "healthy", "up"):
                    return True
                if status in ("error", "down", "unavailable"):
                    return False
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _runtime_field(rt: Any, name: str, default: str = "") -> str:
    if isinstance(rt, dict):
        return str(rt.get(name, default) or default)
    return str(getattr(rt, name, default) or default)


def validate_runtime_health(
    runtimes: Sequence[Any],
    runtime_id: str | None,
    *,
    phase: Phase = Phase.POST_HEALTH,
    live_probe: bool = True,
) -> list[ValidationIssue]:
    """Validate mapped runtime availability (static DOQL status + optional live probe)."""
    if not runtime_id or not runtimes:
        return []

    by_id = {_runtime_field(rt, "id"): rt for rt in runtimes if _runtime_field(rt, "id")}
    rt = by_id.get(runtime_id)
    if rt is None:
        return []

    status = _runtime_field(rt, "status", "unknown")
    if status == "unavailable":
        return [
            ValidationIssue(
                code="runtime.unavailable",
                field_name="runtime",
                message=(
                    f"Środowisko wykonania `{runtime_id}` jest niedostępne w mapie DOQL "
                    f"(status=unavailable)."
                ),
                phase=phase,
                kind="blocked",
                resolution="blocked",
                meta={"runtime_id": runtime_id},
            )
        ]

    health_url = _runtime_field(rt, "health")
    if live_probe and health_url and not probe_health_endpoint(health_url):
        return [
            ValidationIssue(
                code="runtime.health_failed",
                field_name="runtime",
                message=(
                    f"Środowisko `{runtime_id}` nie odpowiada na health check: {health_url}"
                ),
                phase=phase,
                kind="blocked",
                resolution="blocked",
                meta={"runtime_id": runtime_id, "health": health_url},
            )
        ]

    return []


def validate_runtime_health_for_intent(
    runtimes: Sequence[Any],
    intent: str | None,
    *,
    phase: Phase = Phase.POST_HEALTH,
    live_probe: bool = True,
) -> list[ValidationIssue]:
    return validate_runtime_health(
        runtimes,
        runtime_id_for_intent(intent),
        phase=phase,
        live_probe=live_probe,
    )
