"""DOQL task context reader — mirrors nlp2dsl_sdk/doql_context.py format."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DoqlArtifact:
    path: str
    kind: str = "file"
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoqlCommand:
    name: str
    description: str = ""
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    runtime: str = ""
    protocol: str = ""
    transport: str = ""


@dataclass
class DoqlRuntime:
    id: str
    kind: str = "worker"
    url: str = ""
    status: str = "unknown"
    roles: list[str] = field(default_factory=list)


@dataclass
class DoqlTaskContext:
    example_name: str = ""
    generated_at: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[DoqlArtifact] = field(default_factory=list)
    runtimes: list[DoqlRuntime] = field(default_factory=list)
    commands: list[DoqlCommand] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    workflow_history: dict[str, Any] = field(default_factory=dict)
    autofill: bool = True
    sync_auto_execute: bool = False
    attachment_required: bool = False
    generate_invoice_if_missing: bool = True

    def command(self, name: str) -> DoqlCommand | None:
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None

    def required_fields_for(self, action: str) -> list[str] | None:
        cmd = self.command(action)
        if cmd and cmd.required:
            return list(cmd.required)
        return None

    def runtime_for(self, action: str) -> str | None:
        cmd = self.command(action)
        if cmd and cmd.runtime:
            return cmd.runtime
        rt = self._runtime_id_for_action(action)
        if rt and any(r.id == rt for r in self.runtimes):
            return rt
        return rt

    @staticmethod
    def _runtime_id_for_action(action: str) -> str | None:
        if action.startswith("mullm_"):
            return "delegate:mullm"
        if action.startswith("system_"):
            return "orchestrator:nlp-service"
        return "executor:worker"


_BLOCK_RE = re.compile(
    r"(environment|data|conversation|capabilities|workflow_history)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}",
    re.DOTALL,
)
_ARTIFACT_RE = re.compile(
    r"artifacts\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_RUNTIME_RE = re.compile(
    r"runtimes\s*\[[^\]]*\]\s*\{([^}]*)\}",
    re.DOTALL,
)
_COMMAND_RE = re.compile(
    r"commands\s*\[[^\]]*\]\s*\{([^}]*)\}",
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


def _parse_runtime_body(body: str) -> DoqlRuntime:
    kv = _parse_block_body(body)
    return DoqlRuntime(
        id=str(kv.get("id", "")),
        kind=str(kv.get("kind", "worker")),
        url=str(kv.get("url", "")),
        status=str(kv.get("status", "unknown")),
        roles=_split_csv(str(kv.get("roles", ""))),
    )


def _parse_command_body(body: str) -> DoqlCommand:
    kv = _parse_block_body(body)
    return DoqlCommand(
        name=str(kv.get("name", kv.get("action", ""))),
        description=str(kv.get("description", "")),
        required=_split_csv(str(kv.get("required", ""))),
        optional=_split_csv(str(kv.get("optional", ""))),
        runtime=str(kv.get("runtime", "")),
        protocol=str(kv.get("protocol", "")),
        transport=str(kv.get("transport", "")),
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

    for body in _RUNTIME_RE.findall(text):
        rt = _parse_runtime_body(body)
        if rt.id:
            ctx.runtimes.append(rt)

    for body in _COMMAND_RE.findall(text):
        cmd = _parse_command_body(body)
        if cmd.name:
            ctx.commands.append(cmd)

    return ctx


def resolve_doql_context_path(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
    raw = os.environ.get("NLP2DSL_DOQL_CONTEXT", "").strip()
    if raw:
        path = Path(raw)
        if path.is_file():
            return path
    example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
    if example_dir:
        root = Path(example_dir)
        for candidate in (
            root / ".nlp2dsl" / "registry" / "environment.doql.less",
            root / ".nlp2dsl" / "environment.doql.less",
        ):
            if candidate.is_file():
                return candidate
    return None


def merge_inline_context(ctx: DoqlTaskContext, inline: dict[str, Any]) -> DoqlTaskContext:
    if not inline:
        return ctx
    merged_data = dict(ctx.data)
    for key, value in inline.items():
        if value is None:
            continue
        camel = {
            "attachmentPath": "attachment_path",
            "attachment_path": "attachment_path",
            "amount": "send_invoice.amount",
            "to": "send_invoice.to",
            "currency": "send_invoice.currency",
            "attachment_required": "conversation.attachment_required",
            "generate_invoice_if_missing": "conversation.generate_invoice_if_missing",
        }
        mapped = camel.get(key, key)
        conv_key = key if key.startswith("conversation.") else mapped
        if conv_key.startswith("conversation."):
            flag = conv_key.split(".", 1)[1]
            if flag == "attachment_required":
                ctx.attachment_required = bool(value)
            elif flag == "generate_invoice_if_missing":
                ctx.generate_invoice_if_missing = bool(value)
            elif flag == "autofill":
                ctx.autofill = bool(value)
            elif flag == "sync_auto_execute":
                ctx.sync_auto_execute = bool(value)
            continue
        if key in ("sync_auto_execute", "auto_execute"):
            ctx.sync_auto_execute = bool(value)
            continue
        if key in ("example_dir", "NLP2DSL_EXAMPLE_DIR"):
            continue
        merged_data[mapped] = value
        if key in ("amount", "to", "currency", "attachment_path", "attachmentPath"):
            short = mapped.split(".")[-1] if "." in mapped else mapped
            merged_data.setdefault(short, value)
        elif "." in key and key.count(".") == 1:
            _, short = key.split(".", 1)
            merged_data.setdefault(short, value)
    ctx.data = merged_data
    return ctx


def autofill_entities(
    entities: dict[str, Any],
    missing_refs: list[str],
    ctx: DoqlTaskContext,
    *,
    intent: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    if not ctx.autofill or not ctx.data:
        return entities, []

    updated = dict(entities)
    filled: list[str] = []
    alias_map = {"attachment": "attachment_path", "attachmentpath": "attachment_path"}

    for ref in list(missing_refs):
        if "." in ref:
            action, field = ref.split(".", 1)
        else:
            action = intent or "send_invoice"
            field = ref

        field = alias_map.get(field.lower(), field)
        if field == "attachment_path" and not ctx.attachment_required:
            continue
        candidates = [f"{action}.{field}", field, f"send_invoice.{field}"]
        value = None
        for key in candidates:
            if key in ctx.data and ctx.data[key] is not None:
                value = ctx.data[key]
                break
        if value is None:
            for art in ctx.artifacts:
                if field == "attachment_path" and art.path:
                    if not ctx.attachment_required:
                        break
                    value = art.path
                    break
                if field in art.values and art.values[field] is not None:
                    value = art.values[field]
                    break
        if value is not None and updated.get(field) is None:
            updated[field] = value
            filled.append(ref)

    return updated, filled
