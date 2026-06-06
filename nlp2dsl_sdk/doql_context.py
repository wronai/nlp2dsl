"""DOQL system map — backward-compatible re-export shim (see nlp2dsl_sdk/doql/)."""

from __future__ import annotations

from .doql.models import (
    DoqlAccess,
    DoqlArtifact,
    DoqlCommand,
    DoqlProcessPolicy,
    DoqlResource,
    DoqlRuntime,
    DoqlTaskContext,
)
from .doql.parse import (
    collect_task_context,
    enrich_task_context_from_client,
    load_commands_from_services_yaml,
    load_doql_context,
    load_platform_map,
    parse_fixture_metadata,
)
from .doql.render import render_doql_context, write_doql_context
from .doql.runtime import (
    autofill_entities,
    context_inline_payload,
    load_doql_inline_from_env,
    resolve_doql_context_path,
)

__all__ = [
    "DoqlAccess",
    "DoqlArtifact",
    "DoqlCommand",
    "DoqlProcessPolicy",
    "DoqlResource",
    "DoqlRuntime",
    "DoqlTaskContext",
    "autofill_entities",
    "collect_task_context",
    "context_inline_payload",
    "enrich_task_context_from_client",
    "load_commands_from_services_yaml",
    "load_doql_context",
    "load_doql_inline_from_env",
    "load_platform_map",
    "parse_fixture_metadata",
    "render_doql_context",
    "resolve_doql_context_path",
    "write_doql_context",
]
