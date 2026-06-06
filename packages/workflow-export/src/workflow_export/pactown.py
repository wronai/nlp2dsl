"""Pactown ecosystem manifests for composed nlp2dsl + workflow services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULT_BACKEND_URL = "http://localhost:8010"
DEFAULT_NLP_URL = "http://localhost:8012"
DEFAULT_WORKER_URL = "http://localhost:8004"


def platform_service_readme(
    *,
    name: str,
    description: str,
    python_deps: list[str],
    run_command: str,
    main_py: str | None = None,
) -> str:
    """Minimal markpact README for a long-running HTTP service (pactown contract)."""
    deps_body = "\n".join(python_deps)
    parts = [
        f"# {name}",
        "",
        description,
        "",
        f"```text markpact:deps python",
        deps_body,
        "```",
        "",
    ]
    if main_py:
        parts.extend(
            [
                f"```python markpact:file path={main_py}",
                "# Service code managed outside this README (see docker compose).",
                "```",
                "",
            ]
        )
    parts.extend(
        [
            "```bash markpact:run",
            run_command,
            "```",
            "",
            "```http markpact:test http",
            "GET /health EXPECT 200",
            "```",
            "",
        ]
    )
    return "\n".join(parts)


def nlp2dsl_platform_ecosystem(
    *,
    name: str = "nlp2dsl-platform",
    version: str = "0.1.0",
    description: str = "nlp2dsl backend + nlp-service + worker stack",
    base_port: int = 8010,
    sandbox_root: str = "./.pactown-sandboxes",
    workflow_readme: str = "services/report-and-email/README.md",
    backend_url: str = DEFAULT_BACKEND_URL,
    nlp_url: str = DEFAULT_NLP_URL,
    worker_url: str = DEFAULT_WORKER_URL,
) -> dict[str, Any]:
    """Ecosystem YAML wiring platform services + exported workflow README."""
    return {
        "name": name,
        "version": version,
        "description": description,
        "base_port": base_port,
        "sandbox_root": sandbox_root,
        "services": {
            "nlp-service": {
                "readme": "services/nlp-service/README.md",
                "port": 8012,
                "health_check": "/health",
                "timeout": 30,
            },
            "backend": {
                "readme": "services/backend/README.md",
                "port": 8010,
                "health_check": "/health",
                "timeout": 30,
                "depends_on": [
                    {"name": "nlp-service", "env_var": "NLP_SERVICE_URL"},
                    {"name": "worker", "env_var": "WORKER_URL"},
                ],
            },
            "worker": {
                "readme": "services/worker/README.md",
                "port": 8004,
                "health_check": "/health",
                "timeout": 30,
            },
            "report-and-email": {
                "readme": workflow_readme,
                "port": None,
                "timeout": 60,
                "depends_on": [
                    {"name": "backend", "endpoint": backend_url, "env_var": "NLP2DSL_BACKEND_URL"},
                ],
            },
        },
        "metadata": {
            "nlp_service_url": nlp_url,
            "backend_url": backend_url,
            "worker_url": worker_url,
            "note": "Workflow service is review-only; execute via backend API.",
        },
    }


def ecosystem_to_yaml(ecosystem: Mapping[str, Any]) -> str:
    return yaml.safe_dump(dict(ecosystem), allow_unicode=True, sort_keys=False)


@dataclass
class PactownExportBundle:
    root: Path
    ecosystem_yaml: Path
    service_readmes: list[Path] = field(default_factory=list)


def export_pactown_bundle(
    out_dir: Path | str,
    *,
    markpact_readme: Path | str,
    ecosystem: Mapping[str, Any] | None = None,
) -> PactownExportBundle:
    """Write pactown ecosystem + platform service README stubs."""
    root = Path(out_dir)
    services_dir = root / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    markpact_src = Path(markpact_readme)
    workflow_dst = services_dir / "report-and-email" / "README.md"
    workflow_dst.parent.mkdir(parents=True, exist_ok=True)
    workflow_dst.write_text(markpact_src.read_text(encoding="utf-8"), encoding="utf-8")

    platform_readmes: list[tuple[str, str, list[str], str]] = [
        (
            "nlp-service",
            "nlp-service — NLP → DSL pipeline",
            ["fastapi", "uvicorn", "httpx", "pydantic"],
            "uvicorn app.main:app --host 0.0.0.0 --port ${MARKPACT_PORT:-8012}",
        ),
        (
            "backend",
            "backend — workflow orchestration API",
            ["fastapi", "uvicorn", "httpx", "pydantic"],
            "uvicorn app.main:app --host 0.0.0.0 --port ${MARKPACT_PORT:-8010}",
        ),
        (
            "worker",
            "worker — imperative action executors",
            ["fastapi", "uvicorn", "httpx"],
            "uvicorn worker:app --host 0.0.0.0 --port ${MARKPACT_PORT:-8004}",
        ),
    ]

    service_paths: list[Path] = [workflow_dst]
    for svc_name, desc, deps, run_cmd in platform_readmes:
        svc_path = services_dir / svc_name / "README.md"
        svc_path.parent.mkdir(parents=True, exist_ok=True)
        svc_path.write_text(
            platform_service_readme(
                name=svc_name,
                description=desc,
                python_deps=deps,
                run_command=run_cmd,
            ),
            encoding="utf-8",
        )
        service_paths.append(svc_path)

    eco = dict(ecosystem or nlp2dsl_platform_ecosystem())
    eco.setdefault("services", {})["report-and-email"] = {
        "readme": "services/report-and-email/README.md",
        "port": None,
        "timeout": 60,
        "depends_on": [{"name": "backend", "env_var": "NLP2DSL_BACKEND_URL"}],
    }

    eco_path = root / "nlp2dsl-platform.pactown.yaml"
    eco_path.write_text(ecosystem_to_yaml(eco), encoding="utf-8")

    return PactownExportBundle(
        root=root,
        ecosystem_yaml=eco_path,
        service_readmes=service_paths,
    )
