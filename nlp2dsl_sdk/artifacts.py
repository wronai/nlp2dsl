"""
Write transparent NLP → DSL → CMD → process artifacts under examples/*/.nlp2dsl/.

Artifacts:
  environment.doql.less   — env snapshot (DOQL-style, secrets masked)
  commands.testql.toon.yaml — runnable testql commands for this example
  manifest.yaml         — index of queries and artifact paths
  pipeline/{slug}.json|.yaml — full workflow API response per query
  process/{slug}.process.yaml — layered trace: nlp → dsl → cmd → process
  services.yaml         — available workflow actions (when client online)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .doql_context import collect_task_context, enrich_task_context_from_client, write_doql_context
from .encoding import utf8_open

_PROCESS_FORMAT = "nlp2dsl.process.v1"
_MANIFEST_FORMAT = "nlp2dsl.example_manifest.v1"
_ENV_KEYS = (
    "NLP2DSL_BACKEND_URL",
    "NLP2DSL_NLP_SERVICE_URL",
    "NLP2DSL_WORKER_URL",
    "NLP2DSL_TIMEOUT",
    "NLP_ENRICH_MISSING",
    "NLP2DSL_UTF8",
    "NLP_CHAT_MODE",
    "LLM_MODEL",
    "OPENROUTER_API_KEY",
    "NLP2CMD_INTEGRATION",
    "NLP2CMD_INTRACT_GATE",
)


def example_artifact_root(example_dir: Path | str) -> Path:
    return Path(example_dir).resolve() / ".nlp2dsl"


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    if not slug:
        slug = "query"
    return slug[:max_len].rstrip("-")


def _mask_secret(value: str) -> str:
    if not value or len(value) < 8:
        return "***"
    return f"{value[:4]}…{value[-4:]}"


def collect_environment() -> dict[str, str]:
    out: dict[str, str] = {}
    for key in _ENV_KEYS:
        raw = os.environ.get(key)
        if raw is None:
            continue
        if "KEY" in key or "SECRET" in key or "TOKEN" in key:
            out[key] = _mask_secret(raw)
        else:
            out[key] = raw
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    return out


def write_environment_doql(
    artifact_root: Path,
    example_name: str,
    env: Mapping[str, str],
    *,
    example_dir: Path | None = None,
    queries_meta: Sequence[Mapping[str, Any]] | None = None,
) -> Path:
    from .artifact_layout import ensure_layout, write_registry
    from .doql_context import render_doql_context

    artifact_root.mkdir(parents=True, exist_ok=True)
    ensure_layout(artifact_root)
    ctx = collect_task_context(
        example_dir or artifact_root.parent,
        example_name=example_name,
        environment=dict(env),
        queries=list(queries_meta or []),
    )
    return write_registry(artifact_root, render_doql_context(ctx))


def build_process_trace(
    query: str,
    result: Mapping[str, Any],
    *,
    mode: str = "auto",
    layer_ir: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """NLP → DSL → CMD → process service layers from a workflow_from_text result."""
    dsl = result.get("dsl") or result.get("partial_workflow")
    steps_out: list[dict[str, Any]] = []

    nlp_layer: dict[str, Any] = {
        "layer": "nlp",
        "action": "parse_intent",
        "input": {"query": query, "mode": mode},
        "output": {
            "status": result.get("status"),
            "missing_fields": result.get("missing_fields", []),
            "prompt_user": result.get("prompt_user"),
        },
    }
    if layer_ir:
        nlp_layer["output"]["intent_ir"] = layer_ir.get("intent_ir")
        nlp_layer["output"]["execution_plan_ir"] = layer_ir.get("execution_plan_ir")
    steps_out.append(nlp_layer)

    dsl_layer: dict[str, Any] = {
        "layer": "dsl",
        "action": "map_to_workflow",
        "output": {
            "workflow_name": (dsl or {}).get("name"),
            "trigger": (dsl or {}).get("trigger"),
            "step_count": len((dsl or {}).get("steps", [])),
            "steps": (dsl or {}).get("steps", []),
        },
    }
    steps_out.append(dsl_layer)

    cmd_steps = []
    for step in (dsl or {}).get("steps", []):
        action = step.get("action", "")
        config = step.get("config", {})
        cmd_steps.append({
            "action": action,
            "config": config,
            "endpoint": _action_endpoint(action),
            "transport": _action_transport(action),
        })

    steps_out.append({
        "layer": "cmd",
        "action": "build_service_requests",
        "output": {"commands": cmd_steps},
    })

    execution = result.get("result") or result.get("execution")
    process_layer: dict[str, Any] = {
        "layer": "process",
        "action": "execute_workflow",
        "output": {
            "status": (execution or {}).get("status") if execution else None,
            "workflow_id": (execution or {}).get("workflow_id") if execution else None,
            "steps": (execution or {}).get("steps", []) if execution else [],
        },
    }
    if result.get("status") == "incomplete":
        process_layer["output"]["blocked"] = True
        process_layer["output"]["reason"] = "missing_fields"
    steps_out.append(process_layer)

    return {
        "format": _PROCESS_FORMAT,
        "query": query,
        "mode": mode,
        "status": result.get("status"),
        "pipeline": steps_out,
    }


def _action_endpoint(action: str) -> str:
    if action.startswith("system_"):
        return f"POST /system/execute {{action: {action}}}"
    if action.startswith("notify_"):
        return f"POST /workflow/execute (notify provider)"
    return "POST /workflow/from-text → worker"


def _action_transport(action: str) -> str:
    if action.startswith("system_"):
        return "nlp-service/system"
    if action in ("generate_code",):
        return "nlp-service/llm"
    return "backend→worker"


def write_query_artifacts(
    artifact_root: Path,
    query: str,
    result: Mapping[str, Any],
    *,
    mode: str = "auto",
    layer_ir: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    artifact_root.mkdir(parents=True, exist_ok=True)
    slug = _slugify(query)
    pipeline_dir = artifact_root / "pipeline"
    process_dir = artifact_root / "process"
    pipeline_dir.mkdir(exist_ok=True)
    process_dir.mkdir(exist_ok=True)

    paths: dict[str, str] = {}

    json_path = pipeline_dir / f"{slug}.json"
    with utf8_open(json_path, "w") as fh:
        json.dump({"query": query, "mode": mode, "result": dict(result)}, fh, indent=2, ensure_ascii=False)
    paths["pipeline_json"] = str(json_path.relative_to(artifact_root))

    yaml_path = pipeline_dir / f"{slug}.yaml"
    payload = {"query": query, "mode": mode, "result": dict(result)}
    yaml_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    paths["pipeline_yaml"] = str(yaml_path.relative_to(artifact_root))

    process = build_process_trace(query, result, mode=mode, layer_ir=layer_ir)
    process_path = process_dir / f"{slug}.process.yaml"
    process_path.write_text(
        yaml.safe_dump(process, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    paths["process_yaml"] = str(process_path.relative_to(artifact_root))

    return {"slug": slug, **paths}


def write_manifest(
    artifact_root: Path,
    *,
    example_id: str,
    example_title: str,
    queries: Sequence[Mapping[str, Any]],
) -> Path:
    artifact_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": _MANIFEST_FORMAT,
        "example_id": example_id,
        "title": example_title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries": list(queries),
        "artifacts": {
            "environment": "registry/environment.doql.less",
            "testql": "commands.testql.toon.yaml",
            "services": "services.yaml",
            "pipeline_dir": "pipeline/",
            "process_dir": "process/",
        },
    }
    path = artifact_root / "manifest.yaml"
    path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def write_testql_commands(
    artifact_root: Path,
    *,
    example_id: str,
    example_dir: Path,
    queries: Sequence[str],
    repo_root: Path | None = None,
) -> Path:
    artifact_root.mkdir(parents=True, exist_ok=True)
    repo = repo_root or example_dir.parents[1]  # examples/NN → repo root
    rel_example = example_dir.relative_to(repo) if example_dir.is_relative_to(repo) else example_dir.name

    lines = [
        f"# SCENARIO: Example {example_id}",
        "# TYPE: cli",
        f"# GENERATED: true",
        f"# PIPELINE: NLP → DSL → CMD → process",
        "",
        "CONFIG[3]{key, value}:",
        "  cli_command, python3 main.py",
        "  timeout_ms, 120000",
        f"  example_dir, {rel_example}",
        "",
        f"# Run full example scenario",
        f'SHELL "cd {rel_example} && python3 main.py" 120000',
        "ASSERT_EXIT_CODE 0",
        "",
    ]

    for i, query in enumerate(queries, 1):
        safe = query.replace('"', '\\"')
        lines.extend([
            f"# Query {i}: {query[:60]}",
            f'SHELL "nlp2dsl run \\"{safe}\\" --json" 30000',
            "ASSERT_EXIT_CODE 0",
            "",
        ])

    path = artifact_root / "commands.testql.toon.yaml"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_services_snapshot(artifact_root: Path, actions: Sequence[Mapping[str, Any]]) -> Path | None:
    if not actions:
        return None
    artifact_root.mkdir(parents=True, exist_ok=True)
    path = artifact_root / "services.yaml"
    payload = {
        "format": "nlp2dsl.services.v1",
        "count": len(actions),
        "actions": [
            {
                "name": a.get("name"),
                "description": a.get("description"),
                "required": a.get("required", []),
                "optional": a.get("optional", {}),
            }
            for a in actions
        ],
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


class ExampleArtifactWriter:
    """Accumulates query results and flushes .nlp2dsl/ on finalize()."""

    def __init__(
        self,
        example_dir: Path | str,
        *,
        example_id: str | None = None,
        title: str = "",
    ):
        from .artifact_layout import clean_artifact_root

        self.example_dir = Path(example_dir).resolve()
        self.example_id = example_id or self.example_dir.name
        self.title = title or self.example_id
        self.artifact_root = example_artifact_root(self.example_dir)
        clean_artifact_root(self.example_dir)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._queries_meta: list[dict[str, Any]] = []
        self._query_texts: list[str] = []

    def record(
        self,
        query: str,
        result: Mapping[str, Any],
        *,
        mode: str = "auto",
        layer_ir: Mapping[str, Any] | None = None,
    ) -> dict[str, str]:
        self._query_texts.append(query)
        paths = write_query_artifacts(
            self.artifact_root,
            query,
            result,
            mode=mode,
            layer_ir=layer_ir,
        )
        meta = {
            "query": query,
            "mode": mode,
            "status": result.get("status"),
            "missing_fields": result.get("missing_fields", []),
            "actions": _extract_actions(result),
            **paths,
        }
        self._queries_meta.append(meta)
        return meta

    def finalize(self, client: Any | None = None) -> Path:
        env = collect_environment()
        from .doql_registry import merge_registry_observations
        from .system_map_generator import generate_system_map
        from .system_map_render import render_system_map_doql

        system_map = generate_system_map(
            self.example_dir,
            example_id=self.example_id,
            environment=env,
            queries=self._queries_meta,
            client=client,
        )
        legacy = self.artifact_root / "registry" / "environment.doql.less"
        if not legacy.is_file():
            legacy = self.artifact_root / "environment.doql.less"
        merge_registry_observations(system_map, legacy)
        from .artifact_layout import ensure_layout, write_registry

        ensure_layout(self.artifact_root)
        doql_path = write_registry(self.artifact_root, render_system_map_doql(system_map))
        os.environ.setdefault("NLP2DSL_DOQL_CONTEXT", str(doql_path))
        write_testql_commands(
            self.artifact_root,
            example_id=self.example_id,
            example_dir=self.example_dir,
            queries=self._query_texts or ["(no queries recorded)"],
        )
        if client is not None:
            try:
                actions = client.workflow_actions()
                write_services_snapshot(self.artifact_root, actions)
            except Exception:
                pass
        write_manifest(
            self.artifact_root,
            example_id=self.example_id,
            example_title=self.title,
            queries=self._queries_meta,
        )
        return self.artifact_root


def _extract_actions(result: Mapping[str, Any]) -> list[str]:
    dsl = result.get("dsl") or result.get("partial_workflow")
    if not dsl:
        return []
    return [str(s.get("action", "")) for s in dsl.get("steps", [])]


def get_example_writer() -> ExampleArtifactWriter | None:
    """Return writer when NLP2DSL_EXAMPLE_DIR env is set (examples/main.py bootstrap)."""
    raw = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if not raw:
        return None
    title = os.environ.get("NLP2DSL_EXAMPLE_TITLE", "")
    return ExampleArtifactWriter(raw, title=title)
