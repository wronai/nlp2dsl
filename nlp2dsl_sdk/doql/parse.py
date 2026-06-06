"""DOQL parse — read environment.doql.less into DoqlTaskContext."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import (
    DoqlAccess,
    DoqlArtifact,
    DoqlCommand,
    DoqlProcessPolicy,
    DoqlResource,
    DoqlRuntime,
    DoqlTaskContext,
)
from ..system_map_ir import ProfileValidationIR

_BLOCK_RE = re.compile(
    r"(environment|data|conversation|capabilities|workflow_history|process|process_access|paths)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}",
    re.DOTALL,
)
_ARTIFACT_RE = re.compile(r"artifacts\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_COMMAND_RE = re.compile(r"commands\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_RESOURCE_RE = re.compile(r"resources\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_ACCESS_RE = re.compile(r"access\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_RUNTIME_RE = re.compile(r"runtimes\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_VALIDATION_RE = re.compile(r"validations\s*\[[^\]]*\]\s*\{([^}]*)\}", re.DOTALL)
_KV_RE = re.compile(
    r"(\w+(?:\.\w+)*)\s*:\s*(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*'|[^;]+)\s*;",
)

_PROCESS_STRING_FIELDS: dict[str, str] = {
    "mode": "mode",
    "nlp_parser": "nlp_parser",
    "llm_reasoning": "llm_reasoning",
    "ask_user": "ask_user",
}
_PROCESS_FLOAT_FIELDS: dict[str, str] = {
    "nlp_confidence_min": "nlp_confidence_min",
    "llm_temperature": "llm_temperature",
}
_PROCESS_INT_FIELDS: dict[str, str] = {"autonomous_max_rounds": "autonomous_max_rounds"}
_PROCESS_BOOL_FIELDS: dict[str, str] = {
    "nlp_enrich_missing": "nlp_enrich_missing",
    "autonomous": "autonomous_enabled",
    "intract_gate": "intract_gate",
    "intract_enforce_clarification": "intract_enforce_clarification",
}


def _parse_value(raw: str) -> Any:
    text = raw.strip().rstrip(",")
    if not text:
        return ""
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('\\"', '"')
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("\\'", "'")
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _parse_block_body(body: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for match in _KV_RE.finditer(body):
        out[match.group(1)] = _parse_value(match.group(2))
    return out


def _split_csv(raw: str) -> list[str]:
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _parse_command_body(body: str) -> DoqlCommand:
    kv = _parse_block_body(body)
    name = str(kv.get("name", kv.get("action", "")))
    return DoqlCommand(
        name=name,
        description=str(kv.get("description", "")),
        required=_split_csv(str(kv.get("required", ""))),
        optional=_split_csv(str(kv.get("optional", ""))),
        runtime=str(kv.get("runtime", "")),
        transport=str(kv.get("transport", "backend→worker")),
        endpoint=str(kv.get("endpoint", "POST /workflow/run")),
    )


def _parse_resource_body(body: str) -> DoqlResource:
    kv = _parse_block_body(body)
    return DoqlResource(
        id=str(kv.get("id", "")),
        title=str(kv.get("title", "")),
        connector=str(kv.get("connector", "")),
        uri_patterns=_split_csv(str(kv.get("uri_patterns", kv.get("uri", "")))),
    )


def _parse_access_body(body: str) -> DoqlAccess:
    kv = _parse_block_body(body)
    return DoqlAccess(
        agent=str(kv.get("agent", "")),
        resource_area=str(kv.get("resource_area", kv.get("resource", ""))),
        actions=_split_csv(str(kv.get("actions", ""))),
        effect=str(kv.get("effect", "allow")),
    )


def _parse_runtime_body(body: str) -> DoqlRuntime:
    kv = _parse_block_body(body)
    return DoqlRuntime(
        id=str(kv.get("id", "")),
        kind=str(kv.get("kind", "worker")),
        url=str(kv.get("url", "")),
        uri=str(kv.get("uri", "")),
        health=str(kv.get("health", "")),
        docker_profile=str(kv.get("docker_profile", "")),
        model=str(kv.get("model", "")),
        roles=_split_csv(str(kv.get("roles", ""))),
        status=str(kv.get("status", "unknown")),
    )


def _parse_validation_body(body: str) -> ProfileValidationIR:
    kv = _parse_block_body(body)
    return ProfileValidationIR(
        code=str(kv.get("code", "")),
        action=str(kv.get("action", "")),
        status=str(kv.get("status", "")),
        path=str(kv.get("path", "")),
    )


def _parse_artifact_body(body: str) -> DoqlArtifact:
    kv = _parse_block_body(body)
    values: dict[str, Any] = {}
    path = str(kv.get("path", ""))
    kind = str(kv.get("kind", "file"))
    for key in ("to", "amount", "currency", "attachment_path", "recipient"):
        if key in kv:
            values[key] = kv[key]
    return DoqlArtifact(path=path, kind=kind, values=values)


def _apply_context_metadata(ctx: DoqlTaskContext, text: str) -> None:
    name_match = re.search(r'environment\[name="([^"]+)"\]', text)
    if name_match:
        ctx.example_name = name_match.group(1)
    gen_match = re.search(r"//\s*generated:\s*(\S+)", text)
    if gen_match:
        ctx.generated_at = gen_match.group(1)


def _apply_conversation_block(ctx: DoqlTaskContext, kv: dict[str, Any]) -> None:
    ctx.autofill = bool(kv.get("autofill", True))
    ctx.sync_auto_execute = bool(kv.get("sync_auto_execute", False))
    ctx.attachment_required = bool(kv.get("attachment_required", False))
    ctx.generate_invoice_if_missing = bool(kv.get("generate_invoice_if_missing", True))
    ctx.strict_pdf = bool(kv.get("strict_pdf", False))


def _apply_capabilities_block(ctx: DoqlTaskContext, kv: dict[str, Any]) -> None:
    if "actions" in kv:
        raw = str(kv["actions"]).strip('"')
        ctx.capabilities = [action.strip() for action in raw.split(",") if action.strip()]
        return
    ctx.capabilities = sorted(str(key) for key in kv)


def _apply_process_block(ctx: DoqlTaskContext, kv: dict[str, Any]) -> None:
    for key, attr in _PROCESS_STRING_FIELDS.items():
        if key in kv:
            setattr(ctx.process, attr, str(kv[key]))
    for key, attr in _PROCESS_FLOAT_FIELDS.items():
        if key in kv:
            setattr(ctx.process, attr, float(kv[key]))
    for key, attr in _PROCESS_INT_FIELDS.items():
        if key in kv:
            setattr(ctx.process, attr, int(kv[key]))
    for key, attr in _PROCESS_BOOL_FIELDS.items():
        if key in kv:
            setattr(ctx.process, attr, bool(kv[key]))


def _apply_process_access_block(ctx: DoqlTaskContext, kv: dict[str, Any]) -> None:
    if "agent" in kv:
        ctx.process.agent = str(kv["agent"])
    if "allow_areas" in kv:
        ctx.process.allow_resource_areas = _split_csv(str(kv["allow_areas"]))
    if "deny_areas" in kv:
        ctx.process.deny_resource_areas = _split_csv(str(kv["deny_areas"]))


def _apply_paths_block(ctx: DoqlTaskContext, kv: dict[str, Any]) -> None:
    if "read" in kv:
        ctx.process.paths_read = _split_csv(str(kv["read"]))
    if "write" in kv:
        ctx.process.paths_write = _split_csv(str(kv["write"]))


def _apply_context_block(ctx: DoqlTaskContext, block_type: str, kv: dict[str, Any]) -> None:
    if block_type == "environment":
        ctx.environment = {str(k): str(v) for k, v in kv.items()}
    elif block_type == "data":
        ctx.data.update(kv)
    elif block_type == "conversation":
        _apply_conversation_block(ctx, kv)
    elif block_type == "capabilities":
        _apply_capabilities_block(ctx, kv)
    elif block_type == "workflow_history":
        ctx.workflow_history = dict(kv)
    elif block_type == "process":
        _apply_process_block(ctx, kv)
    elif block_type == "process_access":
        _apply_process_access_block(ctx, kv)
    elif block_type == "paths":
        _apply_paths_block(ctx, kv)


def _append_collection_blocks(ctx: DoqlTaskContext, text: str) -> None:
    for body in _ARTIFACT_RE.findall(text):
        ctx.artifacts.append(_parse_artifact_body(body))
    for body in _COMMAND_RE.findall(text):
        cmd = _parse_command_body(body)
        if cmd.name:
            ctx.commands.append(cmd)
    for body in _RESOURCE_RE.findall(text):
        res = _parse_resource_body(body)
        if res.id:
            ctx.resources.append(res)
    for body in _ACCESS_RE.findall(text):
        grant = _parse_access_body(body)
        if grant.agent:
            ctx.access.append(grant)
    for body in _RUNTIME_RE.findall(text):
        rt = _parse_runtime_body(body)
        if rt.id:
            ctx.runtimes.append(rt)
    for body in _VALIDATION_RE.findall(text):
        spec = _parse_validation_body(body)
        if spec.code:
            ctx.validations.append(spec)


def load_doql_context(path: Path | str) -> DoqlTaskContext:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    ctx = DoqlTaskContext()
    _apply_context_metadata(ctx, text)
    for block_type, body in _BLOCK_RE.findall(text):
        _apply_context_block(ctx, block_type, _parse_block_body(body))
    _append_collection_blocks(ctx, text)
    return ctx


def _repo_root_from_example(example_dir: Path) -> Path:
    if example_dir.parent.name == "examples":
        return example_dir.parent.parent
    return example_dir.parent


def _command_transport(action: str) -> tuple[str, str]:
    if action.startswith("system_"):
        return "nlp-service/system", f"POST /system/execute {{action: {action}}}"
    if action.startswith("notify_"):
        return "backend→worker", "POST /workflow/run"
    return "backend→worker", "POST /workflow/run"


def load_platform_map(repo_root: Path) -> tuple[list[DoqlResource], list[DoqlAccess]]:
    """Resources + access grants from nlp2dsl.yaml."""
    resources: list[DoqlResource] = []
    access: list[DoqlAccess] = []
    config_path = repo_root / "nlp2dsl.yaml"
    if not config_path.is_file():
        return resources, access
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError:
        return resources, access

    for area in payload.get("resource_areas") or []:
        if not isinstance(area, dict):
            continue
        resources.append(
            DoqlResource(
                id=str(area.get("id", "")),
                title=str(area.get("title", "")),
                connector=str(area.get("connector", "")),
                uri_patterns=[str(u) for u in area.get("uri_patterns") or []],
            )
        )

    for agent_id, agent in (payload.get("agents") or {}).items():
        if not isinstance(agent, dict):
            continue
        for grant in agent.get("grants") or []:
            if not isinstance(grant, dict):
                continue
            actions_raw = grant.get("actions") or []
            access.append(
                DoqlAccess(
                    agent=str(agent_id),
                    resource_area=str(grant.get("resource_area", grant.get("uri_pattern", ""))),
                    actions=[str(a) for a in actions_raw] if isinstance(actions_raw, list) else [str(actions_raw)],
                    effect=str(grant.get("effect", "allow")),
                )
            )
    return resources, access


def load_commands_from_services_yaml(path: Path) -> list[DoqlCommand]:
    if not path.is_file():
        return []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return []
    out: list[DoqlCommand] = []
    for action in payload.get("actions") or []:
        if not isinstance(action, dict):
            continue
        name = str(action.get("name", ""))
        if not name:
            continue
        transport, endpoint = _command_transport(name)
        req = action.get("required") or []
        opt = action.get("optional") or {}
        out.append(
            DoqlCommand(
                name=name,
                description=str(action.get("description", "")),
                required=[str(r) for r in req] if isinstance(req, list) else [],
                optional=sorted(str(k) for k in opt) if isinstance(opt, dict) else [],
                transport=transport,
                endpoint=endpoint,
            )
        )
    return out


def enrich_task_context_from_client(ctx: DoqlTaskContext, client: Any) -> DoqlTaskContext:
    """Add live capabilities, command schemas, and workflow history when backend is online."""
    try:
        actions = client.workflow_actions()
        if isinstance(actions, list):
            ctx.capabilities = sorted(
                str(a.get("name", a)) if isinstance(a, dict) else str(a) for a in actions
            )
            if not ctx.commands:
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    name = str(action.get("name", ""))
                    if not name:
                        continue
                    transport, endpoint = _command_transport(name)
                    req = action.get("required") or []
                    opt = action.get("optional") or {}
                    ctx.commands.append(
                        DoqlCommand(
                            name=name,
                            description=str(action.get("description", "")),
                            required=[str(r) for r in req] if isinstance(req, list) else [],
                            optional=sorted(str(k) for k in opt) if isinstance(opt, dict) else [],
                            transport=transport,
                            endpoint=endpoint,
                        )
                    )
    except Exception:
        pass
    try:
        hist = client.workflow_history(limit=5)
        if isinstance(hist, list):
            ctx.workflow_history = {
                "count": len(hist),
                "recent_ids": [
                    str(h.get("workflow_id", h.get("id", ""))) for h in hist[:5] if isinstance(h, dict)
                ],
            }
    except Exception:
        pass
    return ctx


def parse_fixture_metadata(path: Path) -> dict[str, Any]:
    """Parse simple key: value lines from fixtures/invoice-request.txt style files."""
    if not path.is_file():
        return {}
    out: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key in ("odbiorca", "recipient", "to"):
            out["send_invoice.to"] = value
        elif key in ("kwota", "amount"):
            num = re.search(r"[\d.]+", value.replace(",", "."))
            if num:
                out["send_invoice.amount"] = float(num.group())
            if "PLN" in value.upper():
                out["send_invoice.currency"] = "PLN"
            elif "EUR" in value.upper():
                out["send_invoice.currency"] = "EUR"
        elif key in ("waluta", "currency"):
            out["send_invoice.currency"] = value
    return out


def collect_task_context(
    example_dir: Path | str,
    *,
    example_name: str,
    environment: Mapping[str, str] | None = None,
    queries: list[Mapping[str, Any]] | None = None,
) -> DoqlTaskContext:
    root = Path(example_dir).resolve()
    artifact_root = root / ".nlp2dsl"
    ctx = DoqlTaskContext(
        example_name=example_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        environment=dict(environment or {}),
        autofill=True,
    )

    fixture_dirs = [root / "fixtures", artifact_root / "fixtures"]
    seen: set[Path] = set()
    for fixtures_dir in fixture_dirs:
        if not fixtures_dir.is_dir():
            continue
        for fix_path in sorted(fixtures_dir.iterdir()):
            if not fix_path.is_file() or fix_path in seen:
                continue
            seen.add(fix_path)
            values = parse_fixture_metadata(fix_path) if fix_path.suffix == ".txt" else {}
            for k, v in values.items():
                ctx.data.setdefault(k, v)
            try:
                rel = str(fix_path.relative_to(root))
            except ValueError:
                try:
                    rel = str(fix_path.relative_to(artifact_root))
                except ValueError:
                    rel = fix_path.name
            if fix_path.suffix.lower() in (".pdf", ".json"):
                ctx.data.setdefault("send_invoice.attachment_path", rel)
            ctx.artifacts.append(
                DoqlArtifact(
                    path=rel,
                    kind="metadata" if fix_path.suffix == ".txt" else "file",
                    values={k.split(".")[-1] if "." in k else k: v for k, v in values.items()},
                )
            )

    if queries:
        for q in queries:
            for action in q.get("actions") or []:
                ctx.data.setdefault(f"{action}.from_query", q.get("query", ""))

    repo_root = _repo_root_from_example(root)
    ctx.resources, ctx.access = load_platform_map(repo_root)
    ctx.commands = load_commands_from_services_yaml(artifact_root / "services.yaml")

    from ..invoice_policy import apply_invoice_context

    apply_invoice_context(ctx)
    return ctx
