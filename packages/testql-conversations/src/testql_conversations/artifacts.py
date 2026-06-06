"""Write conversation trace + human-readable transcript to examples/*/.nlp2dsl/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml


def _routing_summary(data: Mapping[str, Any]) -> str | None:
    routing = data.get("routing")
    if not isinstance(routing, dict):
        return None
    parts: list[str] = []
    for key in ("mode", "parser", "intent", "domain", "confidence"):
        if key in routing and routing[key] is not None:
            parts.append(f"{key}={routing[key]}")
    return ", ".join(parts) if parts else None


def _format_transcript_header(trace: Mapping[str, Any]) -> list[str]:
    return [
        "# Conversation transcript",
        "",
        f"- **conversation_id:** `{trace.get('conversation_id', '?')}`",
        f"- **status:** {trace.get('status', 'unknown')}",
        f"- **generated:** {trace.get('generated_at', datetime.now(timezone.utc).isoformat())}",
        "",
    ]


def _format_execution_steps(execution: Mapping[str, Any]) -> list[str]:
    lines = [f"- **execution:** status=`{execution.get('status', '?')}`"]
    for step in execution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = step.get("action", "?")
        step_status = step.get("status", "?")
        result = step.get("result")
        lines.append(f"  - `{action}` → {step_status}: {result}")
    return lines


def _format_turn(idx: int, turn: Mapping[str, Any]) -> list[str]:
    role = turn.get("role", "?")
    text = turn.get("text", "")
    endpoint = turn.get("endpoint", "")
    response = turn.get("response") if isinstance(turn.get("response"), dict) else {}

    lines = [f"## Turn {idx} — {role}"]
    if endpoint:
        lines.append(f"- **endpoint:** `{endpoint}`")
    lines.append(f"- **user/system text:** {text!r}")

    status = response.get("status")
    if status:
        lines.append(f"- **nlp2dsl status:** `{status}`")
    missing = response.get("missing")
    if missing:
        lines.append(f"- **missing fields:** {', '.join(str(m) for m in missing)}")
    routing = _routing_summary(response)
    if routing:
        lines.append(f"- **parser/LLM routing:** {routing}")
    message = response.get("message")
    if message:
        lines.append(f"- **assistant message:** {message}")
    dsl = response.get("dsl")
    if isinstance(dsl, dict):
        steps = dsl.get("steps") or []
        actions = [str(s.get("action", "")) for s in steps if isinstance(s, dict)]
        lines.append(f"- **workflow:** `{dsl.get('name', '?')}` → {', '.join(actions) or '(no steps)'}")
    execution = response.get("execution")
    if isinstance(execution, dict):
        lines.extend(_format_execution_steps(execution))
    lines.append("")
    return lines


def _format_validations(validations: list[Any]) -> list[str]:
    lines = ["## Validations"]
    for v in validations:
        if not isinstance(v, dict):
            continue
        mark = "✅" if v.get("passed") else "❌"
        lines.append(f"- {mark} {v.get('id', 'check')}: {v.get('summary', '')}")
    lines.append("")
    return lines


def format_transcript(trace: Mapping[str, Any]) -> str:
    """Render user ↔ nlp2dsl dialog with parser/LLM hints."""
    lines = _format_transcript_header(trace)

    for idx, turn in enumerate(trace.get("turns") or [], start=1):
        if isinstance(turn, dict):
            lines.extend(_format_turn(idx, turn))

    validations = trace.get("validations") or []
    if validations:
        lines.extend(_format_validations(validations))

    return "\n".join(lines).rstrip() + "\n"


def write_conversation_artifacts(
    artifact_root: Path | str,
    trace: Mapping[str, Any],
    *,
    scenario_name: str = "conversation.scenario.yaml",
) -> dict[str, Path]:
    """Persist trace JSON, YAML, and markdown transcript under .nlp2dsl/."""
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)

    payload = dict(trace)
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("scenario", scenario_name)

    json_path = root / "conversation.trace.json"
    yaml_path = root / "conversation.trace.yaml"
    md_path = root / "conversation.transcript.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    md_path.write_text(format_transcript(payload), encoding="utf-8")

    return {"json": json_path, "yaml": yaml_path, "markdown": md_path}
