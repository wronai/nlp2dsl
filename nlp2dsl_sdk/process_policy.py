"""Process policy — platform defaults + per-example rules from example-profiles.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .system_map_ir import (
    ProcessAccessScopeIR,
    ProcessPathsIR,
    ProcessPolicyIR,
    SystemMapIR,
)
from .system_map_runtimes import load_example_profile

_MODE_PRESETS: dict[str, dict[str, Any]] = {
    "deterministic": {
        "nlp_parser": "rules_first",
        "nlp_confidence_min": 0.85,
        "nlp_enrich_missing": False,
        "llm_reasoning": "shallow",
        "autonomous_enabled": True,
        "ask_user": "when_exhausted",
    },
    "balanced": {
        "nlp_parser": "auto",
        "nlp_confidence_min": 0.5,
        "nlp_enrich_missing": False,
        "llm_reasoning": "shallow",
        "autonomous_enabled": True,
        "ask_user": "when_exhausted",
    },
    "reactive": {
        "nlp_parser": "auto",
        "nlp_confidence_min": 0.35,
        "nlp_enrich_missing": True,
        "llm_reasoning": "deep",
        "autonomous_enabled": True,
        "ask_user": "when_exhausted",
    },
}

_NESTED_KEYS = frozenset({"nlp", "autonomous", "intract", "llm", "access", "paths", "conversation"})


def _as_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def _deep_merge_process(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(base)
    for key, val in override.items():
        if key in _NESTED_KEYS and isinstance(val, Mapping):
            nested = dict(out.get(key) or {})
            nested.update(dict(val))
            out[key] = nested
        else:
            out[key] = val
    return out


def _load_nlp2dsl_payload(repo_root: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name in ("nlp2dsl.yaml", "nlp2dsl.local.yaml"):
        path = repo_root / name
        if not path.is_file():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except OSError:
            continue
        if not isinstance(doc, dict):
            continue
        if not payload:
            payload = doc
            continue
        if isinstance(doc.get("defaults"), dict):
            defaults = dict(payload.get("defaults") or {})
            for dk, dv in doc["defaults"].items():
                if isinstance(dv, dict) and isinstance(defaults.get(dk), dict):
                    defaults[dk] = {**defaults[dk], **dv}
                else:
                    defaults[dk] = dv
            payload["defaults"] = defaults
    return payload


def load_platform_process_defaults(repo_root: Path | str | None = None) -> dict[str, Any]:
    """Read nlp2dsl.yaml defaults.process (merged with nlp2dsl.local.yaml)."""
    root = Path(repo_root) if repo_root else Path.cwd()
    payload = _load_nlp2dsl_payload(root)
    defaults = payload.get("defaults") or {}
    block = defaults.get("process")
    return dict(block) if isinstance(block, dict) else {}


def _merge_access(raw: Mapping[str, Any] | None) -> ProcessAccessScopeIR:
    if not raw:
        return ProcessAccessScopeIR()
    return ProcessAccessScopeIR(
        agent=str(raw.get("agent") or ""),
        allow_resource_areas=_as_list(raw.get("allow_resource_areas") or raw.get("allow_areas")),
        deny_resource_areas=_as_list(raw.get("deny_resource_areas") or raw.get("deny_areas")),
    )


def _merge_paths(raw: Mapping[str, Any] | None) -> ProcessPathsIR:
    if not raw:
        return ProcessPathsIR()
    read = raw.get("artifacts_read") or raw.get("read")
    write = raw.get("artifacts_write") or raw.get("write")
    return ProcessPathsIR(read=_as_list(read), write=_as_list(write))


def process_policy_from_profile_block(raw: Mapping[str, Any] | None) -> ProcessPolicyIR:
    """Build ProcessPolicyIR from merged process YAML block."""
    if not raw:
        return ProcessPolicyIR()

    mode = str(raw.get("mode") or "balanced")
    preset = dict(_MODE_PRESETS.get(mode, _MODE_PRESETS["balanced"]))
    _apply_nlp_policy(preset, _mapping_block(raw, "nlp"))
    _apply_autonomous_policy(preset, _mapping_block(raw, "autonomous"))
    llm_temperature = _apply_llm_policy(preset, _mapping_block(raw, "llm"))
    intract_gate, intract_clarify = _intract_flags(_mapping_block(raw, "intract"))

    access = _merge_access(raw.get("access") if isinstance(raw.get("access"), Mapping) else None)
    paths = _merge_paths(raw.get("paths") if isinstance(raw.get("paths"), Mapping) else None)

    return _process_policy_from_parts(
        mode=_normalized_mode(mode),
        preset=preset,
        llm_temperature=llm_temperature,
        intract_gate=intract_gate,
        intract_clarify=intract_clarify,
        access=access,
        paths=paths,
    )


def _mapping_block(raw: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = raw.get(key)
    return value if isinstance(value, Mapping) else None


def _apply_nlp_policy(preset: dict[str, Any], nlp: Mapping[str, Any] | None) -> None:
    if not nlp:
        return
    if nlp.get("parser"):
        preset["nlp_parser"] = str(nlp["parser"])
    if "confidence_min" in nlp:
        preset["nlp_confidence_min"] = float(nlp["confidence_min"])
    if "enrich_missing" in nlp:
        preset["nlp_enrich_missing"] = bool(nlp["enrich_missing"])


def _apply_autonomous_policy(preset: dict[str, Any], autonomous: Mapping[str, Any] | None) -> None:
    if not autonomous:
        return
    if "enabled" in autonomous:
        preset["autonomous_enabled"] = bool(autonomous["enabled"])
    if "max_rounds" in autonomous:
        preset["autonomous_max_rounds"] = int(autonomous["max_rounds"])
    if autonomous.get("ask_user"):
        preset["ask_user"] = str(autonomous["ask_user"])


def _apply_llm_policy(preset: dict[str, Any], llm: Mapping[str, Any] | None) -> float | None:
    if not llm:
        return None
    if llm.get("reasoning"):
        preset["llm_reasoning"] = str(llm["reasoning"])
    if "temperature" in llm:
        return float(llm["temperature"])
    return None


def _intract_flags(intract: Mapping[str, Any] | None) -> tuple[bool, bool]:
    if not intract:
        return False, False
    return (
        bool(intract.get("gate", False)),
        bool(intract.get("enforce_clarification", False)),
    )


def _normalized_mode(mode: str) -> str:
    return mode if mode in _MODE_PRESETS else "balanced"


def _process_policy_from_parts(
    *,
    mode: str,
    preset: Mapping[str, Any],
    llm_temperature: float | None,
    intract_gate: bool,
    intract_clarify: bool,
    access: ProcessAccessScopeIR,
    paths: ProcessPathsIR,
) -> ProcessPolicyIR:
    return ProcessPolicyIR(
        mode=mode,
        nlp_parser=preset["nlp_parser"],
        nlp_confidence_min=float(preset["nlp_confidence_min"]),
        nlp_enrich_missing=bool(preset["nlp_enrich_missing"]),
        llm_reasoning=preset["llm_reasoning"],
        llm_temperature=llm_temperature,
        autonomous_enabled=bool(preset.get("autonomous_enabled", True)),
        autonomous_max_rounds=int(preset.get("autonomous_max_rounds", 8)),
        ask_user=preset.get("ask_user", "when_exhausted"),
        intract_gate=intract_gate,
        intract_enforce_clarification=intract_clarify,
        access=access,
        paths=paths,
    )


def _merge_conversation_from_profile(ir: SystemMapIR, raw: Mapping[str, Any]) -> None:
    conv = raw.get("conversation")
    if not isinstance(conv, Mapping):
        return
    updates: dict[str, Any] = {}
    for key in ("autofill", "attachment_required", "generate_invoice_if_missing", "sync_auto_execute", "strict_pdf"):
        if key in conv:
            updates[key] = bool(conv[key])
    if updates:
        ir.conversation = ir.conversation.model_copy(update=updates)


def merge_process_config(
    *,
    repo_root: Path | str | None = None,
    example_block: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Platform defaults.process ← example-profiles process: override."""
    root = Path(repo_root) if repo_root else Path.cwd()
    platform = load_platform_process_defaults(root)
    if not example_block:
        return platform
    if not platform:
        return dict(example_block)
    return _deep_merge_process(platform, example_block)


def apply_process_policies(
    ir: SystemMapIR,
    *,
    example_id: str | None = None,
    repo_root: Path | str | None = None,
    profile: Mapping[str, Any] | None = None,
) -> None:
    """Merge nlp2dsl.yaml defaults + example-profiles process into SystemMapIR."""
    ex_id = example_id or ir.example_id
    root = Path(repo_root) if repo_root else Path.cwd()
    if profile is None:
        loaded = load_example_profile(ex_id, root)
        profile = loaded or {}

    example_block = profile.get("process") if isinstance(profile.get("process"), Mapping) else None
    merged = merge_process_config(repo_root=root, example_block=example_block)
    if merged:
        ir.process = process_policy_from_profile_block(merged)
        _merge_conversation_from_profile(ir, merged)

    from .validation.profile_checks import apply_profile_validations

    apply_profile_validations(ir, dict(profile) if profile else None)


def effective_nlp_parser_mode(process: ProcessPolicyIR | None) -> str:
    """Map DOQL nlp_parser → runtime parser mode (rules | llm | auto)."""
    if process is None:
        return "auto"
    parser = (process.nlp_parser or "auto").lower()
    if parser in ("rules", "rules_first"):
        return "rules"
    if parser == "llm":
        return "llm"
    return "auto"


def process_policy_to_doql_dict(process: ProcessPolicyIR) -> dict[str, Any]:
    """Flat key map for DOQL process {} block."""
    out: dict[str, Any] = {
        "mode": process.mode,
        "nlp_parser": process.nlp_parser,
        "nlp_confidence_min": process.nlp_confidence_min,
        "nlp_enrich_missing": process.nlp_enrich_missing,
        "llm_reasoning": process.llm_reasoning,
        "autonomous": process.autonomous_enabled,
        "autonomous_max_rounds": process.autonomous_max_rounds,
        "ask_user": process.ask_user,
        "intract_gate": process.intract_gate,
        "intract_enforce_clarification": process.intract_enforce_clarification,
    }
    if process.llm_temperature is not None:
        out["llm_temperature"] = process.llm_temperature
    return out


def process_scope_denied(
    process: ProcessPolicyIR,
    *,
    action: str | None,
    resource_area: str | None,
) -> str | None:
    """Return user message when action is outside process_access scope."""
    if not action:
        return None
    area = (resource_area or "").strip()
    deny = set(process.access.deny_resource_areas or [])
    allow = set(process.access.allow_resource_areas or [])

    if area and area in deny:
        return (
            f"Akcja `{action}` (obszar `{area}`) jest zablokowana polityką procesu "
            f"(process_access.deny_areas)."
        )
    if action.startswith("mullm_") and deny.intersection({"mullm:rag", "mullm", "mullm:*"}):
        return (
            f"Akcja `{action}` wymaga delegacji Mullm, a proces ma wycięty obszar Mullm "
            f"(process_access.deny_areas)."
        )
    if allow and area and area not in allow:
        return (
            f"Akcja `{action}` (obszar `{area}`) nie należy do dozwolonych obszarów procesu "
            f"({', '.join(sorted(allow))})."
        )
    return None
