"""
Reflection model — target plan vs current state after each process decision.

Flow:
  1. build_target_plan() — model realizacji requestu z SystemMapIR / DOQL
  2. reflect() — porównanie z bieżącym stanem + walidacja formatów
  3. context_queries — pętla pytań kontekstowych (co poprawić / uzupełnić)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from .system_map_ir import CommandSchemaIR, SystemMapIR

IssueKind = Literal["missing", "mismatch", "invalid_format", "blocked", "unknown_action"]
Resolution = Literal["autofill", "generate", "ask_user", "fix_format", "blocked", "none"]


class TargetStep(BaseModel):
    action: str
    config: dict[str, Any] = Field(default_factory=dict)


class TargetPlan(BaseModel):
    """Docelowy model realizacji requestu."""

    intent: str
    steps: list[TargetStep] = Field(default_factory=list)
    policies: dict[str, Any] = Field(default_factory=dict)


class ReflectionIssue(BaseModel):
    phase: str
    kind: IssueKind
    field: str
    message: str
    resolution: Resolution = "ask_user"
    source_hint: str | None = None


class ReflectionReport(BaseModel):
    phase: str
    ready: bool
    target: TargetPlan
    current: dict[str, Any] = Field(default_factory=dict)
    issues: list[ReflectionIssue] = Field(default_factory=list)
    context_queries: list[str] = Field(default_factory=list)
    resolutions_available: list[str] = Field(default_factory=list)

    @property
    def primary_context_query(self) -> str | None:
        return self.context_queries[0] if self.context_queries else None


_FIELD_LABELS: dict[str, str] = {
    "amount": "kwotę faktury",
    "to": "adres e-mail odbiorcy",
    "currency": "walutę",
    "attachment_path": "plik faktury (PDF)",
    "subject": "temat wiadomości",
    "body": "treść wiadomości",
}


def _intent_from_response(response: Mapping[str, Any]) -> str:
    dsl = response.get("dsl") or {}
    for step in dsl.get("steps") or []:
        if isinstance(step, dict) and step.get("action"):
            return str(step["action"])
    missing = response.get("missing") or []
    for ref in missing:
        if isinstance(ref, str) and "." in ref:
            return ref.split(".", 1)[0]
    return "send_invoice"


def _entities_from_response(response: Mapping[str, Any]) -> dict[str, Any]:
    entities: dict[str, Any] = {}
    dsl = response.get("dsl") or {}
    for step in dsl.get("steps") or []:
        if isinstance(step, dict):
            entities.update(step.get("config") or {})
    return entities


def _data_lookup(ir: SystemMapIR, action: str, field: str) -> Any:
    for key in (f"{action}.{field}", field, f"send_invoice.{field}"):
        if key in ir.data:
            return ir.data[key]
    return None


def build_target_plan(
    ir: SystemMapIR,
    intent: str,
    entities: Mapping[str, Any] | None = None,
) -> TargetPlan:
    """Zbuduj docelowy model kroków i configu z mapy systemu."""
    entities = dict(entities or {})
    cmd = ir.command(intent)
    config: dict[str, Any] = {}

    if cmd:
        for spec in cmd.fields:
            val = entities.get(spec.name)
            if val is None or (isinstance(val, str) and not val.strip()):
                val = _data_lookup(ir, intent, spec.name)
            if val is not None and not (isinstance(val, str) and not str(val).strip()):
                config[spec.name] = val
            elif not spec.required:
                config.setdefault(spec.name, "" if spec.name == "attachment_path" else None)
    else:
        config.update({k: v for k, v in entities.items() if not str(k).startswith("_")})

    if ir.conversation.attachment_required and intent == "send_invoice":
        if not str(config.get("attachment_path", "")).strip():
            hint = _data_lookup(ir, intent, "attachment_path")
            if hint:
                config["attachment_path"] = hint

    steps = [TargetStep(action=intent, config=config)] if intent else []
    return TargetPlan(
        intent=intent,
        steps=steps,
        policies=ir.conversation.model_dump(),
    )


def _parse_validation_issue(raw: str) -> ReflectionIssue | None:
    if raw.startswith("brak wymaganego pola:"):
        field = raw.split(":", 1)[1].strip()
        return ReflectionIssue(
            phase="validate",
            kind="missing",
            field=field,
            message=raw,
            resolution="ask_user",
        )
    if raw.startswith("brak pola jakości:"):
        field = raw.split(":", 1)[1].strip()
        return ReflectionIssue(
            phase="validate",
            kind="missing",
            field=field,
            message=raw,
            resolution="ask_user",
        )
    if "attachment_path" in raw:
        resolution: Resolution = "fix_format"
        if "nie istnieje" in raw:
            resolution = "generate"
        else:
            resolution = "ask_user"
        return ReflectionIssue(
            phase="validate",
            kind="invalid_format" if "≠" in raw or "FAKTURA" in raw or "PDF" in raw else "missing",
            field="attachment_path",
            message=raw,
            resolution=resolution,
            source_hint="generate_invoice" if "nie istnieje" in raw else None,
        )
    if raw.startswith("to:"):
        return ReflectionIssue(
            phase="validate",
            kind="invalid_format",
            field="to",
            message=raw,
            resolution="fix_format",
        )
    if raw.startswith("amount:"):
        return ReflectionIssue(
            phase="validate",
            kind="invalid_format",
            field="amount",
            message=raw,
            resolution="fix_format",
        )
    if raw.startswith("unknown_action:"):
        return ReflectionIssue(
            phase="validate",
            kind="unknown_action",
            field="action",
            message=raw,
            resolution="blocked",
        )
    return ReflectionIssue(
        phase="validate",
        kind="mismatch",
        field="",
        message=raw,
        resolution="ask_user",
    )


def _missing_vs_target(
    phase: str,
    target: TargetPlan,
    current: Mapping[str, Any],
    ir: SystemMapIR,
) -> list[ReflectionIssue]:
    issues: list[ReflectionIssue] = []
    if not target.steps:
        return issues

    step = target.steps[0]
    cmd = ir.command(step.action)

    required = cmd.required_names if cmd else []
    for field in required:
        target_val = step.config.get(field)
        current_val = current.get(field)
        if target_val is None or (isinstance(target_val, str) and not target_val.strip()):
            if current_val is None or (isinstance(current_val, str) and not str(current_val).strip()):
                hint = _data_lookup(ir, step.action, field)
                resolution: Resolution = "autofill" if hint is not None else "ask_user"
                issues.append(
                    ReflectionIssue(
                        phase=phase,
                        kind="missing",
                        field=field,
                        message=f"brak {field} w bieżącym stanie",
                        resolution=resolution,
                        source_hint=f"data.{step.action}.{field}" if hint is not None else None,
                    )
                )
        elif current_val != target_val and current_val is not None:
            issues.append(
                ReflectionIssue(
                    phase=phase,
                    kind="mismatch",
                    field=field,
                    message=f"{field}: bieżące {current_val!r} ≠ docelowe {target_val!r}",
                    resolution="fix_format",
                )
            )

    if ir.conversation.attachment_required and step.action == "send_invoice":
        if not str(current.get("attachment_path", "")).strip():
            resolution = "generate" if ir.conversation.generate_invoice_if_missing else "ask_user"
            issues.append(
                ReflectionIssue(
                    phase=phase,
                    kind="missing",
                    field="attachment_path",
                    message="brak załącznika faktury (attachment_required)",
                    resolution=resolution,
                    source_hint="generate_invoice" if resolution == "generate" else "fixtures/",
                )
            )

    return issues


def _context_queries_from_issues(issues: Sequence[ReflectionIssue]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    for issue in issues:
        if issue.resolution in ("autofill", "none", "blocked"):
            continue
        if issue.resolution == "generate" and issue.field == "attachment_path":
            q = "Brak pliku faktury — wygenerować załącznik automatycznie (generate_invoice)?"
        elif issue.kind == "missing":
            label = _FIELD_LABELS.get(issue.field, issue.field)
            q = f"Podaj {label}."
        elif issue.kind == "invalid_format" or issue.kind == "mismatch":
            q = f"Popraw {issue.field}: {issue.message}"
        else:
            q = issue.message
        if q not in seen:
            seen.add(q)
            queries.append(q)

    return queries


def _resolutions_available(issues: Sequence[ReflectionIssue], ir: SystemMapIR) -> list[str]:
    out: list[str] = []
    for issue in issues:
        if issue.resolution == "autofill" and issue.source_hint:
            out.append(f"autofill:{issue.source_hint}")
        if issue.resolution == "generate" and ir.conversation.generate_invoice_if_missing:
            out.append("generate:generate_invoice")
    return list(dict.fromkeys(out))


def reflect(
    phase: str,
    target: TargetPlan,
    current: Mapping[str, Any],
    *,
    ir: SystemMapIR | None = None,
    validation_issues: Sequence[str] | None = None,
) -> ReflectionReport:
    """Porównaj bieżący stan z modelem docelowym i zwróć raport refleksji."""
    current_dict = dict(current)
    issues: list[ReflectionIssue] = []

    if ir is not None:
        issues.extend(_missing_vs_target(phase, target, current_dict, ir))

    for raw in validation_issues or []:
        parsed = _parse_validation_issue(str(raw))
        if parsed:
            parsed.phase = phase
            if not any(i.field == parsed.field and i.message == parsed.message for i in issues):
                issues.append(parsed)

    ready = len(issues) == 0
    queries = _context_queries_from_issues(issues)
    resolutions = _resolutions_available(issues, ir) if ir else []

    return ReflectionReport(
        phase=phase,
        ready=ready,
        target=target,
        current=current_dict,
        issues=issues,
        context_queries=queries,
        resolutions_available=resolutions,
    )


def reflect_from_chat_turn(
    ir: SystemMapIR,
    response: Mapping[str, Any],
    phase: str,
    *,
    validation_issues: Sequence[str] | None = None,
) -> ReflectionReport:
    """Refleksja po jednej turze chat (SDK / client-side)."""
    intent = _intent_from_response(response)
    entities = _entities_from_response(response)
    if not entities and response.get("missing"):
        for ref in response.get("missing") or []:
            if isinstance(ref, str) and "." in ref:
                _, field = ref.split(".", 1)
                entities.setdefault(field, None)

    target = build_target_plan(ir, intent, entities)
    if target.steps:
        current = target.steps[0].config
    else:
        current = entities

    status = str(response.get("status", ""))
    if status == "ready" and validation_issues is None:
        from .step_validation import validate_step_config_from_map

        validation_issues = validate_step_config_from_map(ir, intent, current)

    return reflect(
        phase,
        target,
        current,
        ir=ir,
        validation_issues=validation_issues,
    )


def reflect_from_doql_path(
    doql_path: Path | str,
    response: Mapping[str, Any],
    phase: str,
    *,
    validation_issues: Sequence[str] | None = None,
) -> ReflectionReport | None:
    """Load SystemMapIR from DOQL and reflect (client helper)."""
    from .system_map_bridge import doql_file_to_system_map

    path = Path(doql_path)
    if not path.is_file():
        return None
    ir = doql_file_to_system_map(path)
    return reflect_from_chat_turn(ir, response, phase, validation_issues=validation_issues)


def format_reflection_summary(report: ReflectionReport | Mapping[str, Any]) -> str:
    if not isinstance(report, ReflectionReport):
        report = ReflectionReport.model_validate(dict(report))
    if report.ready:
        return f"✓ Refleksja [{report.phase}]: model zgodny — gotowe do kolejnego kroku."

    lines = [f"⚠ Refleksja [{report.phase}]: model wymaga uzupełnienia"]
    for issue in report.issues[:6]:
        lines.append(f"  • {issue.field or '?'}: {issue.message} → {issue.resolution}")
    if report.context_queries:
        lines.append(f"  ? {report.primary_context_query}")
    return "\n".join(lines)
