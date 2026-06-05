"""Bootstrap runtime catalog from example-profiles.yaml + environment hints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .system_map_ir import RuntimeSpecIR

# Default command → runtime when profile includes worker
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

_SYSTEM_ACTION_PREFIX = "system_"
_MULLM_ACTION_PREFIX = "mullm_"


def _repo_root_from_example(example_dir: Path) -> Path:
    if example_dir.parent.name == "examples":
        return example_dir.parent.parent
    return example_dir.parent


def load_example_profile(example_id: str, repo_root: Path | None = None) -> dict[str, Any] | None:
    root = repo_root or Path.cwd()
    path = root / "examples" / "example-profiles.yaml"
    if not path.is_file():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return None
    examples = payload.get("examples") or {}
    profile = examples.get(example_id)
    return profile if isinstance(profile, dict) else None


def resolve_command_runtime(action: str, *, profile: dict[str, Any] | None = None) -> str:
    if action.startswith(_MULLM_ACTION_PREFIX):
        return "delegate:mullm"
    if action.startswith(_SYSTEM_ACTION_PREFIX):
        return "orchestrator:nlp-service"
    services = (profile or {}).get("services") or []
    if action in _WORKER_ACTIONS and "worker" in services:
        return "executor:worker"
    return "executor:worker"


def build_runtimes_for_example(
    example_id: str,
    *,
    example_dir: Path | str,
    environment: Mapping[str, str] | None = None,
) -> list[RuntimeSpecIR]:
    """Materialize runtimes[] from example-profiles.yaml + env URLs."""
    root = Path(example_dir).resolve()
    repo_root = _repo_root_from_example(root)
    profile = load_example_profile(example_id, repo_root) or {}
    services = list(profile.get("services") or [])
    docker_profiles = list(profile.get("docker_profiles") or [])
    env = dict(environment or {})

    backend_url = env.get("NLP2DSL_BACKEND_URL", "http://localhost:8010")
    nlp_url = env.get("NLP2DSL_NLP_SERVICE_URL", "http://localhost:8012")
    worker_url = env.get("NLP2DSL_WORKER_URL", "http://localhost:8004")
    llm_model = env.get("LLM_MODEL", "openrouter/openai/gpt-5-mini")
    llm_available = bool(env.get("OPENROUTER_API_KEY") or env.get("OPENAI_API_KEY"))

    runtimes: list[RuntimeSpecIR] = []

    if "nlp-service" in services or profile.get("conversation"):
        runtimes.append(
            RuntimeSpecIR(
                id="orchestrator:nlp-service",
                kind="orchestrator",
                url=nlp_url,
                health="GET /health",
                roles=["nlp_parse", "dsl_map", "autofill", "preflight"],
                status="available",
            )
        )

    if "backend" in services:
        runtimes.append(
            RuntimeSpecIR(
                id="gateway:backend",
                kind="gateway",
                url=backend_url,
                health="GET /health",
                roles=["workflow_dispatch", "history"],
                status="available",
            )
        )

    if "worker" in services:
        runtimes.append(
            RuntimeSpecIR(
                id="executor:worker",
                kind="worker",
                url=worker_url,
                health="GET /health",
                docker_profile=",".join(docker_profiles) if docker_profiles else None,
                roles=sorted(_WORKER_ACTIONS),
                status="available",
            )
        )

    runtimes.append(
        RuntimeSpecIR(
            id="llm:provider",
            kind="llm",
            model=llm_model,
            roles=["intent", "entities", "system_map", "clarification"],
            status="available" if llm_available else "unknown",
        )
    )

    if "postgres" in services:
        runtimes.append(
            RuntimeSpecIR(
                id="store:postgres",
                kind="database",
                uri="postgresql://app@postgres:5432/automation",
                roles=["workflow_history", "idempotency"],
                status="available",
            )
        )

    if "redis" in services:
        runtimes.append(
            RuntimeSpecIR(
                id="cache:redis",
                kind="cache",
                uri="redis://redis:6379/0",
                roles=["conversation_state"],
                status="available",
            )
        )

    if "smtp-mock" in services or "invoice" in docker_profiles or "email" in docker_profiles:
        runtimes.append(
            RuntimeSpecIR(
                id="mock:smtp",
                kind="mock",
                url="http://localhost:8025",
                docker_profile="invoice,email",
                roles=["email_delivery_test"],
                status="available" if "smtp-mock" in services else "unknown",
            )
        )

    runtimes.append(
        RuntimeSpecIR(
            id="delegate:mullm",
            kind="external",
            roles=["filesystem", "rag", "shell_delegated"],
            status="unavailable",
        )
    )

    return runtimes
