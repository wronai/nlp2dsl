"""ActionContract + workflow DSL → markpact README (human-readable publish layer)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from dsl_contracts import ActionContract, action_contracts_from_catalog

DEFAULT_BACKEND_URL = "http://localhost:8010"


def contract_to_yaml_dict(contract: ActionContract) -> dict[str, Any]:
    """Serialize ActionContract for markpact:file blocks."""
    optional = contract.optional
    if optional and all(v is None for v in optional.values()):
        optional = {k: None for k in optional}
    return {
        "name": contract.name,
        "version": contract.version,
        "description": contract.description,
        "category": contract.category,
        "required": list(contract.required),
        "optional": optional,
        "quality_required": list(contract.quality_required),
        "aliases": list(contract.aliases),
        "execution": {
            "backend": contract.execution.backend,
            "mode": contract.execution.mode,
            "side_effect": contract.execution.side_effect,
            "idempotency": contract.execution.idempotency,
            "approval_required": contract.execution.approval_required,
        },
    }


def contract_to_yaml_string(contract: ActionContract) -> str:
    return yaml.safe_dump(
        contract_to_yaml_dict(contract),
        allow_unicode=True,
        sort_keys=False,
    ).strip()


def composite_workflow_spec(
    dsl: Mapping[str, Any],
    *,
    contracts: Mapping[str, ActionContract] | None = None,
) -> dict[str, Any]:
    """Build workflow metadata from DSL + optional contracts."""
    steps_out: list[dict[str, Any]] = []
    for step in dsl.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        config = dict(step.get("config") or {})
        entry: dict[str, Any] = {"action": action, "config": config}
        if contracts and action in contracts:
            entry["contract_version"] = contracts[action].version
            entry["execution_backend"] = contracts[action].execution.backend
        steps_out.append(entry)
    return {
        "name": str(dsl.get("name") or "workflow"),
        "trigger": dsl.get("trigger", "manual"),
        "steps": steps_out,
    }


def _yaml_file_block(path: str, body: str, *, lang: str = "yaml") -> str:
    return f"```{lang} markpact:file path={path}\n{body.rstrip()}\n```"


def _contracts_section(contracts: Mapping[str, ActionContract]) -> list[str]:
    lines: list[str] = []
    for name in sorted(contracts):
        rel = f"contracts/{name}.contract.yaml"
        lines.append(_yaml_file_block(rel, contract_to_yaml_string(contracts[name])))
        lines.append("")
    return lines


def workflow_dsl_to_markpact_readme(
    dsl: Mapping[str, Any],
    contracts: Mapping[str, ActionContract],
    *,
    title: str | None = None,
    backend_url: str = DEFAULT_BACKEND_URL,
    source_query: str = "",
) -> str:
    """Render a reviewable markpact README for a validated workflow DSL."""
    workflow_name = str(dsl.get("name") or "workflow")
    display_title = title or f"nlp2dsl workflow: {workflow_name}"
    workflow_spec = composite_workflow_spec(dsl, contracts=contracts)
    workflow_yaml = yaml.safe_dump(workflow_spec, allow_unicode=True, sort_keys=False).strip()
    dsl_json = json.dumps(dict(dsl), indent=2, ensure_ascii=False)

    action_names = sorted(
        {
            str(step.get("action"))
            for step in dsl.get("steps") or []
            if isinstance(step, dict) and step.get("action")
        }
    )
    contracts_for_steps = {
        name: contracts[name] for name in action_names if name in contracts
    }

    parts: list[str] = [
        f"# {display_title}",
        "",
        "Wykonywalny dokument **review/publish** — runtime authority pozostaje w nlp2dsl.",
        "Side effects przechodzą wyłącznie przez `POST /workflow/validate` i `/workflow/execute`.",
        "",
    ]
    if source_query:
        parts.extend([f"**Źródło NL:** {source_query}", ""])

    parts.extend(
        [
            "## Kontrakt workflow",
            "",
            _yaml_file_block(f"workflows/{workflow_name}.workflow.yaml", workflow_yaml),
            "",
            "## Kontrakty akcji",
            "",
        ]
    )
    parts.extend(_contracts_section(contracts_for_steps))

    parts.extend(
        [
            "## DSL (canonical JSON)",
            "",
            _yaml_file_block(f"workflows/{workflow_name}.dsl.json", dsl_json, lang="json"),
            "",
            "## Walidacja (dry-run)",
            "",
            "```bash markpact:run",
            f"# Plan + validate — bez side effects gdy NLP2DSL_EXECUTE=0",
            f"curl -sf -X POST {backend_url.rstrip('/')}/workflow/from-text \\",
            '  -H "Content-Type: application/json" \\',
            f'  -d \'{{"text": {json.dumps(source_query or workflow_name)}, "execute": false, "mode": "rules"}}\'',
            "```",
            "",
            "```http markpact:test http",
            "GET /health EXPECT 200",
            "```",
            "",
        ]
    )
    return "\n".join(parts)


@dataclass
class MarkpactExportBundle:
    """Paths written by export_markpact_bundle."""

    root: Path
    readme: Path
    workflow_yaml: Path
    workflow_json: Path
    contract_files: list[Path] = field(default_factory=list)


def export_markpact_bundle(
    out_dir: Path | str,
    dsl: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    title: str | None = None,
    backend_url: str = DEFAULT_BACKEND_URL,
    source_query: str = "",
) -> MarkpactExportBundle:
    """Write markpact README + contract YAML files under out_dir."""
    root = Path(out_dir)
    contracts_dir = root / "contracts"
    workflows_dir = root / "workflows"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    workflows_dir.mkdir(parents=True, exist_ok=True)

    contracts = action_contracts_from_catalog(catalog)
    workflow_name = str(dsl.get("name") or "workflow")
    workflow_spec = composite_workflow_spec(dsl, contracts=contracts)

    workflow_yaml_path = workflows_dir / f"{workflow_name}.workflow.yaml"
    workflow_yaml_path.write_text(
        yaml.safe_dump(workflow_spec, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    workflow_json_path = workflows_dir / f"{workflow_name}.dsl.json"
    workflow_json_path.write_text(
        json.dumps(dict(dsl), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    contract_files: list[Path] = []
    action_names = {
        str(step.get("action"))
        for step in dsl.get("steps") or []
        if isinstance(step, dict) and step.get("action")
    }
    for name in sorted(action_names):
        contract = contracts.get(name)
        if contract is None:
            continue
        path = contracts_dir / f"{name}.contract.yaml"
        path.write_text(contract_to_yaml_string(contract) + "\n", encoding="utf-8")
        contract_files.append(path)

    readme_path = root / "README.md"
    readme_path.write_text(
        workflow_dsl_to_markpact_readme(
            dsl,
            contracts,
            title=title,
            backend_url=backend_url,
            source_query=source_query,
        )
        + "\n",
        encoding="utf-8",
    )

    return MarkpactExportBundle(
        root=root,
        readme=readme_path,
        workflow_yaml=workflow_yaml_path,
        workflow_json=workflow_json_path,
        contract_files=contract_files,
    )
