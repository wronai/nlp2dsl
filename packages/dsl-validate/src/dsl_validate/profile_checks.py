"""Example-profile validations — parse, evaluate, map to ValidationIssue codes (C3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dsl_contracts.issue import Phase, ValidationIssue
from env2llm.ir import ProfileValidationIR, SystemMapIR

PROFILE_EXECUTION_COMPLETED = "profile.execution_completed"
PROFILE_DSL_ACTION = "profile.dsl_action"
PROFILE_CONVERSATION_EXECUTED = "profile.conversation_executed"
PROFILE_ARTIFACT_EXISTS = "profile.artifact_exists"


@dataclass(frozen=True)
class ProfileCheckContext:
    """Runtime payload for profile validation checks."""

    response: dict[str, Any]
    example_dir: Path | None = None


def _parse_profile_validation_by_code(raw: dict[str, Any]) -> ProfileValidationIR:
    return ProfileValidationIR(
        code=str(raw["code"]),
        action=str(raw.get("action") or ""),
        status=str(raw.get("status") or ""),
        path=str(raw.get("path") or ""),
    )


def _parse_profile_validation_by_type(raw: dict[str, Any]) -> ProfileValidationIR | None:
    vtype = str(raw.get("type", "")).strip()
    if vtype == "dsl_action":
        action = str(raw.get("action", "")).strip()
        if action:
            return ProfileValidationIR(code=PROFILE_DSL_ACTION, action=action)
    if vtype == "execution_completed":
        return ProfileValidationIR(code=PROFILE_EXECUTION_COMPLETED)
    if vtype == "conversation_executed":
        return ProfileValidationIR(code=PROFILE_CONVERSATION_EXECUTED)
    return None


def _parse_profile_validation_shorthand(raw: dict[str, Any]) -> ProfileValidationIR | None:
    if len(raw) != 1:
        return None
    key, value = next(iter(raw.items()))
    key = str(key)
    value_str = str(value)
    if key == "execution_status" and value_str == "completed":
        return ProfileValidationIR(code=PROFILE_EXECUTION_COMPLETED, status=value_str)
    if key == "dsl_action" and value_str:
        return ProfileValidationIR(code=PROFILE_DSL_ACTION, action=value_str)
    if key == "conversation_status" and value_str == "executed":
        return ProfileValidationIR(code=PROFILE_CONVERSATION_EXECUTED, status=value_str)
    if key == "artifact_exists" and value_str:
        return ProfileValidationIR(code=PROFILE_ARTIFACT_EXISTS, path=value_str)
    return None


def parse_profile_validation(raw: Any) -> ProfileValidationIR | None:
    """Parse one validation entry from example-profiles.yaml or scenario YAML."""
    if not isinstance(raw, dict) or not raw:
        return None
    if "code" in raw:
        return _parse_profile_validation_by_code(raw)
    if typed := _parse_profile_validation_by_type(raw):
        return typed
    return _parse_profile_validation_shorthand(raw)


def parse_profile_validations(raw_list: list[Any] | None) -> list[ProfileValidationIR]:
    out: list[ProfileValidationIR] = []
    for raw in raw_list or []:
        spec = parse_profile_validation(raw)
        if spec is not None:
            out.append(spec)
    return out


def load_profile_validations(example_id: str, repo_root: Path | str | None = None) -> list[ProfileValidationIR]:
    from env2llm.runtimes import load_example_profile

    root = Path(repo_root) if repo_root else Path.cwd()
    profile = load_example_profile(example_id, root) or {}
    return parse_profile_validations(profile.get("validations"))


def apply_profile_validations(ir: SystemMapIR, profile: dict[str, Any] | None) -> None:
    if not profile:
        return
    specs = parse_profile_validations(profile.get("validations"))
    if specs:
        ir.validations = specs


def dsl_actions_from_response(response: dict[str, Any]) -> list[str]:
    dsl = response.get("dsl") or response.get("partial_workflow")
    if not isinstance(dsl, dict):
        return []
    return [
        str(step.get("action", ""))
        for step in dsl.get("steps") or []
        if isinstance(step, dict) and step.get("action")
    ]


def execution_completed(response: dict[str, Any]) -> bool:
    execution = response.get("execution") or response.get("result")
    if not isinstance(execution, dict):
        return False
    if execution.get("status") == "completed":
        return True
    steps = execution.get("steps") or []
    return bool(steps) and all(
        isinstance(step, dict) and step.get("status") == "completed" for step in steps
    )


def conversation_executed(response: dict[str, Any]) -> bool:
    if str(response.get("status", "")) == "executed":
        return True
    return execution_completed(response)


def _resolve_artifact_path(path: str, example_dir: Path | None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if example_dir is not None:
        return (example_dir / candidate).resolve()
    return candidate.resolve()


def check_profile_validation(
    spec: ProfileValidationIR,
    ctx: ProfileCheckContext,
    *,
    phase: Phase = Phase.POST_EXECUTE,
) -> ValidationIssue | None:
    """Return a ValidationIssue when the check fails; None when it passes."""
    response = ctx.response

    if spec.code == PROFILE_DSL_ACTION:
        action = spec.action
        if not action:
            return _failed(spec, phase, "brak action w regule profile.dsl_action")
        if action not in dsl_actions_from_response(response):
            return _failed(
                spec,
                phase,
                f"oczekiwano akcji DSL {action!r}, otrzymano {dsl_actions_from_response(response)!r}",
                meta={"action": action, "actions": dsl_actions_from_response(response)},
            )
        return None

    if spec.code == PROFILE_EXECUTION_COMPLETED:
        if not execution_completed(response):
            return _failed(spec, phase, "oczekiwano zakończonego wykonania workflow")
        return None

    if spec.code == PROFILE_CONVERSATION_EXECUTED:
        if not conversation_executed(response):
            return _failed(spec, phase, "oczekiwano statusu conversation executed")
        return None

    if spec.code == PROFILE_ARTIFACT_EXISTS:
        rel = spec.path
        if not rel:
            return _failed(spec, phase, "brak path w regule profile.artifact_exists")
        resolved = _resolve_artifact_path(rel, ctx.example_dir)
        if not resolved.is_file():
            return _failed(
                spec,
                phase,
                f"brak artefaktu: {rel}",
                meta={"path": rel, "resolved": str(resolved)},
            )
        return None

    return _failed(spec, phase, f"nieznany kod walidacji profilu: {spec.code}")


def run_profile_validation_checks(
    specs: list[ProfileValidationIR],
    ctx: ProfileCheckContext,
    *,
    phase: Phase = Phase.POST_EXECUTE,
) -> list[dict[str, Any]]:
    """E2E-friendly results — one dict per spec with passed/summary/code."""
    results: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        issue = check_profile_validation(spec, ctx, phase=phase)
        passed = issue is None
        vid = _validation_id(spec, index)
        if passed:
            summary = _pass_summary(spec)
        else:
            summary = issue.message if issue else "failed"
        results.append(
            {
                "id": vid,
                "code": spec.code,
                "passed": passed,
                "summary": summary,
            }
        )
    return results


def validate_profile_expectations(
    ir: SystemMapIR,
    response: dict[str, Any],
    *,
    example_dir: Path | str | None = None,
    phase: Phase = Phase.POST_EXECUTE,
) -> list[ValidationIssue]:
    ctx = ProfileCheckContext(response=response, example_dir=Path(example_dir) if example_dir else None)
    issues: list[ValidationIssue] = []
    for spec in ir.validations:
        issue = check_profile_validation(spec, ctx, phase=phase)
        if issue is not None:
            issues.append(issue)
    return issues


def response_from_e2e_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Best-effort last API payload from conversation or execution trace JSON."""
    turns = trace.get("turns") or []
    for turn in reversed(turns):
        if not isinstance(turn, dict):
            continue
        response = turn.get("response")
        if isinstance(response, dict):
            return response

    queries = trace.get("queries") or []
    if queries:
        last = queries[-1]
        if isinstance(last, dict):
            result = last.get("result")
            if isinstance(result, dict):
                return result

    if isinstance(trace.get("dsl"), dict) or trace.get("status"):
        return trace
    return {}


def run_validations_from_raw(
    raw_list: list[Any],
    response: dict[str, Any],
    *,
    example_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    specs = parse_profile_validations(raw_list)
    if not specs:
        return []
    ctx = ProfileCheckContext(
        response=response,
        example_dir=Path(example_dir) if example_dir else None,
    )
    return run_profile_validation_checks(specs, ctx)


def _validation_id(spec: ProfileValidationIR, index: int) -> str:
    if spec.code == PROFILE_DSL_ACTION and spec.action:
        return f"profile.dsl_action.{spec.action}"
    if spec.code == PROFILE_ARTIFACT_EXISTS and spec.path:
        safe = spec.path.replace("/", "_").strip("_")
        return f"profile.artifact_exists.{safe}"
    return f"profile.{index}.{spec.code.rsplit('.', 1)[-1]}"


def _pass_summary(spec: ProfileValidationIR) -> str:
    if spec.code == PROFILE_DSL_ACTION:
        return f"dsl action {spec.action!r} present"
    if spec.code == PROFILE_EXECUTION_COMPLETED:
        return "execution completed"
    if spec.code == PROFILE_CONVERSATION_EXECUTED:
        return "conversation executed"
    if spec.code == PROFILE_ARTIFACT_EXISTS:
        return f"artifact exists: {spec.path}"
    return f"{spec.code} ok"


def _failed(
    spec: ProfileValidationIR,
    phase: Phase,
    message: str,
    *,
    meta: dict[str, Any] | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=spec.code,
        field_name=spec.action or spec.path or spec.code,
        message=message,
        phase=phase,
        kind="mismatch",
        resolution="none",
        meta=dict(meta or {}),
    )
