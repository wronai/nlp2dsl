"""
DOQL system map — read/write environment.doql.less.

environment.doql.less is the schema map for nlp2dsl structure generation:
  services/commands, resources, access, artifacts, runtime data, conversation rules.

See docs/doql-system-map.md.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass
class DoqlArtifact:
    path: str
    kind: str = "file"
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoqlRuntime:
    """Execution environment (where command effects run)."""

    id: str
    kind: str = "worker"
    url: str = ""
    uri: str = ""
    health: str = ""
    docker_profile: str = ""
    model: str = ""
    roles: list[str] = field(default_factory=list)
    status: str = "unknown"


@dataclass
class DoqlCommand:
    """Schema kroku CMD — akcja workflow + wymagane pola + runtime + transport."""

    name: str
    description: str = ""
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    runtime: str = ""
    transport: str = "backend→worker"
    endpoint: str = "POST /workflow/run"


@dataclass
class DoqlResource:
    """Zasób / obszar z nlp2dsl.yaml (URI, connector)."""

    id: str
    title: str = ""
    connector: str = ""
    uri_patterns: list[str] = field(default_factory=list)


@dataclass
class DoqlAccess:
    """Grant agenta do zasobu (access_control)."""

    agent: str
    resource_area: str = ""
    actions: list[str] = field(default_factory=list)
    effect: str = "allow"


@dataclass
class DoqlTaskContext:
    example_name: str = ""
    generated_at: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[DoqlArtifact] = field(default_factory=list)
    commands: list[DoqlCommand] = field(default_factory=list)
    resources: list[DoqlResource] = field(default_factory=list)
    access: list[DoqlAccess] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    workflow_history: dict[str, Any] = field(default_factory=dict)
    autofill: bool = True
    sync_auto_execute: bool = False
    attachment_required: bool = False
    generate_invoice_if_missing: bool = True
    runtimes: list[DoqlRuntime] = field(default_factory=list)

    def entity_values(self, action: str) -> dict[str, Any]:
        """Map data keys action.field → entity field names."""
        prefix = f"{action}."
        out: dict[str, Any] = {}
        for key, value in self.data.items():
            if key.startswith(prefix):
                out[key[len(prefix) :]] = value
            elif "." not in key and action == "send_invoice":
                out[key] = value
        return out


_BLOCK_RE = re.compile(
    r"(environment|data|conversation|capabilities|workflow_history)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}",
    re.DOTALL,
)
_ARTIFACT_RE = re.compile(
    r"artifacts\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_COMMAND_RE = re.compile(
    r"commands\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_RESOURCE_RE = re.compile(
    r"resources\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_ACCESS_RE = re.compile(
    r"access\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_RUNTIME_RE = re.compile(
    r"runtimes\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_KV_RE = re.compile(
    r"(\w+(?:\.\w+)*)\s*:\s*(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*'|[^;]+)\s*;",
)


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


def _parse_artifact_body(body: str) -> DoqlArtifact:
    kv = _parse_block_body(body)
    values: dict[str, Any] = {}
    path = str(kv.get("path", ""))
    kind = str(kv.get("kind", "file"))
    for key in ("to", "amount", "currency", "attachment_path", "recipient"):
        if key in kv:
            values[key] = kv[key]
    return DoqlArtifact(path=path, kind=kind, values=values)


def load_doql_context(path: Path | str) -> DoqlTaskContext:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    ctx = DoqlTaskContext()

    name_match = re.search(r'environment\[name="([^"]+)"\]', text)
    if name_match:
        ctx.example_name = name_match.group(1)

    gen_match = re.search(r"//\s*generated:\s*(\S+)", text)
    if gen_match:
        ctx.generated_at = gen_match.group(1)

    for block_type, body in _BLOCK_RE.findall(text):
        kv = _parse_block_body(body)
        if block_type == "environment":
            ctx.environment = {str(k): str(v) for k, v in kv.items()}
        elif block_type == "data":
            ctx.data.update(kv)
        elif block_type == "conversation":
            ctx.autofill = bool(kv.get("autofill", True))
            ctx.sync_auto_execute = bool(kv.get("sync_auto_execute", False))
            ctx.attachment_required = bool(kv.get("attachment_required", False))
            ctx.generate_invoice_if_missing = bool(kv.get("generate_invoice_if_missing", True))
        elif block_type == "capabilities":
            if "actions" in kv:
                raw = str(kv["actions"]).strip('"')
                ctx.capabilities = [a.strip() for a in raw.split(",") if a.strip()]
            else:
                ctx.capabilities = sorted(str(k) for k in kv)
        elif block_type == "workflow_history":
            ctx.workflow_history = dict(kv)

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

    services_path = artifact_root / "services.yaml"
    ctx.commands = load_commands_from_services_yaml(services_path)

    return ctx


def render_doql_context(ctx: DoqlTaskContext) -> str:
    lines = [
        f"// DOQL system map — {ctx.example_name}",
        "// role: schema of available services, commands, resources, artifacts, access",
        f"// generated: {ctx.generated_at}",
        "",
        f'environment[name="{ctx.example_name}"] {{',
    ]
    for key in sorted(ctx.environment):
        if key == "generated_at":
            continue
        safe = str(ctx.environment[key]).replace('"', '\\"')
        lines.append(f'  {key}: "{safe}";')
    lines.append("}")
    lines.append("")

    lines.append("data {")
    for key in sorted(ctx.data):
        val = ctx.data[key]
        if isinstance(val, str):
            safe = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'  {key}: "{safe}";')
        elif isinstance(val, bool):
            lines.append(f"  {key}: {'true' if val else 'false'};")
        else:
            lines.append(f"  {key}: {val};")
    lines.append("}")
    lines.append("")

    for idx, art in enumerate(ctx.artifacts):
        lines.append(f"artifacts[{idx}] {{")
        lines.append(f'  path: "{art.path}";')
        lines.append(f'  kind: "{art.kind}";')
        for k, v in sorted(art.values.items()):
            if isinstance(v, str):
                lines.append(f'  {k}: "{v}";')
            else:
                lines.append(f"  {k}: {v};")
        lines.append("}")
        lines.append("")

    for idx, cmd in enumerate(ctx.commands):
        lines.append(f"commands[{idx}] {{")
        lines.append(f'  name: "{cmd.name}";')
        if cmd.description:
            safe = cmd.description.replace('"', '\\"')
            lines.append(f'  description: "{safe}";')
        if cmd.required:
            lines.append(f'  required: "{",".join(cmd.required)}";')
        if cmd.optional:
            lines.append(f'  optional: "{",".join(cmd.optional)}";')
        lines.append(f'  transport: "{cmd.transport}";')
        lines.append(f'  endpoint: "{cmd.endpoint}";')
        lines.append("}")
        lines.append("")

    for idx, res in enumerate(ctx.resources):
        lines.append(f"resources[{idx}] {{")
        lines.append(f'  id: "{res.id}";')
        if res.title:
            safe = res.title.replace('"', '\\"')
            lines.append(f'  title: "{safe}";')
        if res.connector:
            lines.append(f'  connector: "{res.connector}";')
        if res.uri_patterns:
            lines.append(f'  uri_patterns: "{",".join(res.uri_patterns)}";')
        lines.append("}")
        lines.append("")

    for idx, grant in enumerate(ctx.access):
        lines.append(f"access[{idx}] {{")
        lines.append(f'  agent: "{grant.agent}";')
        if grant.resource_area:
            lines.append(f'  resource_area: "{grant.resource_area}";')
        if grant.actions:
            lines.append(f'  actions: "{",".join(grant.actions)}";')
        lines.append(f'  effect: "{grant.effect}";')
        lines.append("}")
        lines.append("")

    if ctx.capabilities:
        lines.append("")
        lines.append("capabilities {")
        lines.append(f'  actions: "{",".join(ctx.capabilities)}";')
        lines.append("}")

    if ctx.workflow_history:
        lines.append("")
        lines.append("workflow_history {")
        for key in sorted(ctx.workflow_history):
            val = ctx.workflow_history[key]
            if isinstance(val, list):
                lines.append(f'  {key}: "{",".join(str(v) for v in val)}";')
            elif isinstance(val, str):
                lines.append(f'  {key}: "{val}";')
            else:
                lines.append(f"  {key}: {val};")
        lines.append("}")

    lines.append("")
    lines.append("conversation {")
    lines.append(f"  autofill: {'true' if ctx.autofill else 'false'};")
    lines.append(f"  sync_auto_execute: {'true' if ctx.sync_auto_execute else 'false'};")
    lines.append(f"  attachment_required: {'true' if ctx.attachment_required else 'false'};")
    lines.append(
        f"  generate_invoice_if_missing: {'true' if ctx.generate_invoice_if_missing else 'false'};"
    )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def write_doql_context(path: Path | str, ctx: DoqlTaskContext) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_doql_context(ctx), encoding="utf-8")
    return path


def context_inline_payload(ctx: DoqlTaskContext) -> dict[str, Any]:
    """Serialize DOQL data for chat context_json (portable across client/server)."""
    inline = dict(ctx.data)
    for key, value in list(ctx.data.items()):
        if "." in key:
            _, field = key.split(".", 1)
            if field == "attachment_path" and not ctx.attachment_required:
                inline.pop(key, None)
                continue
            inline.setdefault(field, value)
    for art in ctx.artifacts:
        for key, value in art.values.items():
            inline.setdefault(f"send_invoice.{key}", value)
            inline.setdefault(key, value)
    if not ctx.attachment_required:
        inline.pop("attachment_path", None)
        inline.pop("send_invoice.attachment_path", None)
    inline["conversation.autofill"] = ctx.autofill
    if ctx.attachment_required:
        inline["conversation.attachment_required"] = ctx.attachment_required
    if ctx.generate_invoice_if_missing:
        inline["conversation.generate_invoice_if_missing"] = ctx.generate_invoice_if_missing
    if ctx.sync_auto_execute:
        inline["conversation.sync_auto_execute"] = ctx.sync_auto_execute
        inline["sync_auto_execute"] = ctx.sync_auto_execute
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        mount = os.environ.get("NLP2DSL_EXAMPLES_MOUNT", "").strip()
        if mount:
            inline["example_dir"] = str(Path(mount) / Path(example_dir).name)
        else:
            inline["example_dir"] = example_dir
    return inline


def resolve_doql_context_path() -> Path | None:
    from .artifact_layout import resolve_registry_path

    return resolve_registry_path()


def load_doql_inline_from_env() -> dict[str, Any]:
    path = resolve_doql_context_path()
    if not path:
        return {}
    return context_inline_payload(load_doql_context(path))


def autofill_entities(
    entities: dict[str, Any],
    missing_refs: list[str],
    ctx: DoqlTaskContext,
) -> tuple[dict[str, Any], list[str]]:
    """
    Fill missing action.field slots from ctx.data. Returns (updated_entities, filled_keys).
    """
    if not ctx.autofill or not ctx.data:
        return entities, []

    updated = dict(entities)
    filled: list[str] = []

    alias_map = {
        "attachment": "attachment_path",
        "attachmentpath": "attachment_path",
    }

    for ref in list(missing_refs):
        if "." in ref:
            action, field = ref.split(".", 1)
        else:
            action, field = (updated.get("intent") or "send_invoice"), ref

        field = alias_map.get(field.lower(), field)
        candidates = [
            f"{action}.{field}",
            field,
            f"send_invoice.{field}",
        ]
        value = None
        for key in candidates:
            if key in ctx.data and ctx.data[key] is not None:
                value = ctx.data[key]
                break
        if value is None:
            for art in ctx.artifacts:
                if field in art.values and art.values[field] is not None:
                    value = art.values[field]
                    break
        if value is not None and updated.get(field) is None:
            updated[field] = value
            filled.append(ref)

    return updated, filled
