"""
Generate SystemMapIR at runtime via LLM + introspection.

Bootstrap fallback: collect_task_context() → task_context_to_system_map().
Enable LLM path: NLP2DSL_SYSTEM_MAP_LLM=1 and a configured LiteLLM provider.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .doql_context import collect_task_context, enrich_task_context_from_client
from .system_map_bridge import task_context_to_system_map
from .system_map_ir import SystemMapIR
from .system_map_runtimes import load_example_profile

log = logging.getLogger("nlp2dsl.system_map")

LLMComplete = Callable[[str, str], str]

_SYSTEM_PROMPT = """You are a system map generator for nlp2dsl.
Given introspection data about an example environment, emit ONE JSON object
matching nlp2dsl.system_map.v1 (SystemMapIR).

Rules:
- runtimes[]: available execution environments (worker, nlp-service, llm, postgres, …) with status
- commands[]: each action with runtime ref, protocol (workflow/run or propact:*), fields with MIME/schema_ref
- artifacts[]: files with mime.type and schema_ref (e.g. application/pdf → InvoiceDocument)
- resources[] and access[]: from nlp2dsl.yaml hints when present
- data: known field values from fixtures
- conversation: autofill / attachment policies when inferable
- Return ONLY valid JSON, no markdown fences."""


def build_introspection_payload(
    example_dir: Path | str,
    *,
    example_id: str,
    environment: Mapping[str, str] | None = None,
    queries: list[Mapping[str, Any]] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Collect raw signals for LLM (filesystem, YAML, live API)."""
    root = Path(example_dir).resolve()
    artifact_root = root / ".nlp2dsl"
    repo_root = root.parent.parent if root.parent.name == "examples" else root.parent
    profile = load_example_profile(example_id, repo_root)
    payload: dict[str, Any] = {
        "example_id": example_id,
        "example_dir": str(root),
        "example_profile": profile,
        "environment": dict(environment or {}),
        "queries": list(queries or []),
        "fixtures": [],
        "services_yaml": None,
        "nlp2dsl_yaml": None,
        "workflow_actions": None,
    }

    fixtures_dir = artifact_root / "fixtures"
    if fixtures_dir.is_dir():
        for path in sorted(fixtures_dir.iterdir()):
            if path.is_file():
                payload["fixtures"].append(
                    {"path": str(path.relative_to(artifact_root)), "suffix": path.suffix.lower()}
                )

    services_path = artifact_root / "services.yaml"
    if services_path.is_file():
        payload["services_yaml"] = services_path.read_text(encoding="utf-8")[:8000]

    config_path = repo_root / "nlp2dsl.yaml"
    if config_path.is_file():
        payload["nlp2dsl_yaml"] = config_path.read_text(encoding="utf-8")[:8000]

    if client is not None:
        try:
            payload["workflow_actions"] = client.workflow_actions()
        except Exception as exc:
            log.debug("workflow_actions introspection failed: %s", exc)

    return payload


def _bootstrap_system_map(
    example_dir: Path | str,
    *,
    example_id: str,
    environment: Mapping[str, str] | None = None,
    queries: list[Mapping[str, Any]] | None = None,
    client: Any | None = None,
) -> SystemMapIR:
    ctx = collect_task_context(
        example_dir,
        example_name=example_id,
        environment=environment,
        queries=queries,
    )
    if client is not None:
        enrich_task_context_from_client(ctx, client)
    return task_context_to_system_map(ctx, example_dir=example_dir)


def _litellm_complete(system: str, user: str) -> str:
    import litellm

    model = os.getenv("LLM_MODEL", "openrouter/openai/gpt-5-mini")
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
    }
    api_base = os.getenv("LLM_API_BASE")
    if api_base:
        kwargs["api_base"] = api_base
    response = litellm.completion(**kwargs)
    return str(response.choices[0].message.content or "")


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def generate_system_map(
    example_dir: Path | str,
    *,
    example_id: str,
    environment: Mapping[str, str] | None = None,
    queries: list[Mapping[str, Any]] | None = None,
    client: Any | None = None,
    llm_complete: LLMComplete | None = None,
    hints: Mapping[str, Any] | None = None,
) -> SystemMapIR:
    """
    Build SystemMapIR: LLM when enabled, else bootstrap from introspection code.
    """
    use_llm = os.getenv("NLP2DSL_SYSTEM_MAP_LLM", "").strip().lower() in ("1", "true", "yes")
    complete = llm_complete
    if use_llm and complete is None:
        try:
            import litellm  # noqa: F401

            complete = _litellm_complete
        except ImportError:
            log.warning("NLP2DSL_SYSTEM_MAP_LLM set but litellm not installed; using bootstrap")
            use_llm = False

    if not use_llm or complete is None:
        return _bootstrap_system_map(
            example_dir,
            example_id=example_id,
            environment=environment,
            queries=queries,
            client=client,
        )

    introspection = build_introspection_payload(
        example_dir,
        example_id=example_id,
        environment=environment,
        queries=queries,
        client=client,
    )
    schema = SystemMapIR.model_json_schema()
    user = json.dumps(
        {"schema": schema, "introspection": introspection, "hints": dict(hints or {})},
        ensure_ascii=False,
        indent=2,
    )
    try:
        raw = complete(_SYSTEM_PROMPT, user)
        data = _parse_llm_json(raw)
        ir = SystemMapIR.model_validate(data)
        ir.metadata.setdefault("source", "llm")
        return ir
    except Exception:
        log.exception("SystemMapGenerator LLM failed; falling back to bootstrap")
        return _bootstrap_system_map(
            example_dir,
            example_id=example_id,
            environment=environment,
            queries=queries,
            client=client,
        )
