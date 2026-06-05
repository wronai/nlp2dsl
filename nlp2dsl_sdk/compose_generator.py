"""
Generate docker-compose stack + cron artifacts from SystemMapIR / DOQL registry.

Output under `.nlp2dsl/generated/`:
  - docker-compose.stack.yaml
  - ofelia.ini (cron scheduler)
  - run-scheduled-task.sh
  - stack.manifest.yaml
  - services/<name>/Dockerfile (when generated_services present)
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from .system_map_ir import DeploySpecIR, GeneratedServiceIR, ScheduleSpecIR, SystemMapIR
from .system_map_runtimes import load_example_profile


@dataclass
class ComposeGenerationResult:
    stack_compose: Path
    ofelia_ini: Path
    run_script: Path
    manifest: Path
    generated_services: list[Path] = field(default_factory=list)
    docker_profiles: list[str] = field(default_factory=list)
    up_command: str = ""


def _default_deploy(example_id: str, profile: dict[str, Any] | None) -> DeploySpecIR:
    profiles = list((profile or {}).get("docker_profiles") or [])
    if "autonomous-stack" not in profiles:
        profiles.append("autonomous-stack")
    return DeploySpecIR(
        docker_profiles=profiles,
        cron_service=f"{example_id.split('-', 1)[-1]}-cron",
    )


def _default_schedules(example_id: str) -> list[ScheduleSpecIR]:
    return [
        ScheduleSpecIR(
            id="daily-invoice",
            cron="0 9 * * *",
            task="Wyślij fakturę na 1500 PLN do klient@firma.pl",
            workflow_action="send_invoice",
        ),
    ]


def _default_generated_services(example_id: str) -> list[GeneratedServiceIR]:
    short = example_id.split("-", 1)[-1] if "-" in example_id else example_id
    return [
        GeneratedServiceIR(
            name=f"{short}-runner",
            description="Cron-sidecar task runner — invokes backend workflow API",
            build_context=f".nlp2dsl/generated/services/{short}-runner",
            roles=["cron_trigger", "workflow_dispatch"],
        ),
    ]


def enrich_ir_for_stack(
    ir: SystemMapIR,
    *,
    example_id: str,
    profile: dict[str, Any] | None = None,
) -> SystemMapIR:
    """Ensure schedules, deploy block, and generated_services exist on IR."""
    if not ir.schedules:
        ir.schedules = _default_schedules(example_id)
    if ir.deploy is None:
        ir.deploy = _default_deploy(example_id, profile)
    if not ir.generated_services:
        ir.generated_services = _default_generated_services(example_id)
    if "generate_invoice" not in ir.capabilities:
        ir.capabilities = sorted(set(ir.capabilities) | {"generate_invoice", "send_invoice"})
    return ir


def _run_script_content(*, backend_url: str, task: str) -> str:
    safe_task = task.replace('"', '\\"')
    return textwrap.dedent(
        f"""\
        #!/bin/sh
        set -eu
        BACKEND="${{NLP2DSL_BACKEND_URL:-{backend_url}}}"
        echo "[stack-cron] $(date -Iseconds) task={safe_task!r}"
        curl -sf -X POST "$BACKEND/workflow/run" \\
          -H "Content-Type: application/json" \\
          -d '{{"name":"scheduled_stack","trigger":"cron","steps":[{{"action":"send_invoice","config":{{"amount":1500,"to":"klient@firma.pl","currency":"PLN"}}}}]}}' \\
          || echo "[stack-cron] dispatch failed (backend may be offline in dev)"
        """
    )


def _ofelia_ini_content(schedules: list[ScheduleSpecIR], *, script_path: str) -> str:
    lines = ["[job-exec \"runners\"]", "schedule = @every 5s", "no-overlap = true", ""]
    for sched in schedules:
        if not sched.enabled:
            continue
        lines.extend(
            [
                f"[job-local \"{sched.id}\"]",
                f"schedule = {sched.cron}",
                f"command = sh {script_path}",
                "no-overlap = true",
                "",
            ]
        )
    return "\n".join(lines)


def _stack_compose_dict(
    ir: SystemMapIR,
    *,
    example_id: str,
    example_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    dep = ir.deploy or _default_deploy(example_id, None)
    profiles = dep.docker_profiles or ["autonomous-stack"]
    profile_str = ",".join(profiles)

    gen_rel = Path(dep.stack_compose).parent
    services: dict[str, Any] = {
        dep.cron_service: {
            "image": dep.cron_image,
            "profiles": profiles,
            "depends_on": ["backend"],
            "environment": [
                "NLP2DSL_BACKEND_URL=http://backend:8000",
            ],
            "volumes": [
                f"./{gen_rel}/run-scheduled-task.sh:/task.sh:ro",
                f"./{gen_rel}/ofelia.ini:/etc/ofelia/config.ini:ro",
            ],
            "command": "daemon --docker -f /etc/ofelia/config.ini",
            "labels": {
                "nlp2dsl.example": example_id,
                "nlp2dsl.stack": "autonomous-invoice",
            },
        },
    }

    for svc in ir.generated_services:
        if svc.build_context:
            rel_build = svc.build_context
            services[svc.name] = {
                "build": {"context": rel_build},
                "profiles": profiles,
                "environment": ["NLP2DSL_BACKEND_URL=http://backend:8000"],
                "depends_on": ["backend"],
                "labels": {"nlp2dsl.generated_service": svc.name},
            }
        elif svc.image:
            services[svc.name] = {
                "image": svc.image,
                "profiles": profiles,
            }

    return {
        "name": f"nlp2dsl-{example_id}",
        "services": services,
        "x-nlp2dsl": {
            "example_id": example_id,
            "example_dir": str(example_dir),
            "repo_root": str(repo_root),
            "platform_compose": dep.platform_compose,
            "mocks_compose": dep.mocks_compose,
            "docker_profiles": profiles,
            "includes": [
                f"docker compose -f {dep.platform_compose} up -d",
                f"docker compose -f {dep.mocks_compose} --profile {profile_str} up -d",
                f"docker compose -f {gen_rel}/docker-compose.stack.yaml --profile {profile_str} up -d",
            ],
        },
    }


def _runner_dockerfile() -> str:
    return textwrap.dedent(
        """\
        FROM alpine:3.20
        RUN apk add --no-cache curl bash
        COPY run-task.sh /run-task.sh
        RUN chmod +x /run-task.sh
        CMD ["/run-task.sh"]
        """
    )


def generate_stack_compose(
    ir: SystemMapIR,
    *,
    example_dir: Path | str,
    example_id: str | None = None,
    repo_root: Path | str | None = None,
    profile: Mapping[str, Any] | None = None,
) -> ComposeGenerationResult:
    """
    Emit transparent docker-compose stack + cron sidecar under .nlp2dsl/generated/.
    """
    ex_dir = Path(example_dir).resolve()
    ex_id = example_id or ex_dir.name
    root = Path(repo_root).resolve() if repo_root else ex_dir.parent.parent
    prof = dict(profile) if profile else load_example_profile(ex_id, root)

    ir = enrich_ir_for_stack(ir, example_id=ex_id, profile=prof)
    dep = ir.deploy or _default_deploy(ex_id, prof)

    gen_dir = ex_dir / ".nlp2dsl" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    services_dir = gen_dir / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    stack_path = ex_dir / dep.stack_compose
    stack_path.parent.mkdir(parents=True, exist_ok=True)

    run_script = gen_dir / "run-scheduled-task.sh"
    run_script.write_text(
        _run_script_content(
            backend_url="http://localhost:8010",
            task=ir.schedules[0].task if ir.schedules else "Wyślij fakturę",
        ),
        encoding="utf-8",
    )
    run_script.chmod(0o755)

    ofelia_path = gen_dir / "ofelia.ini"
    ofelia_path.write_text(
        _ofelia_ini_content(ir.schedules, script_path="/task.sh"),
        encoding="utf-8",
    )

    stack_payload = _stack_compose_dict(ir, example_id=ex_id, example_dir=ex_dir, repo_root=root)
    stack_path.write_text(
        yaml.safe_dump(stack_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    generated_paths: list[Path] = []
    for svc in ir.generated_services:
        if not svc.build_context:
            continue
        svc_dir = ex_dir / svc.build_context
        svc_dir.mkdir(parents=True, exist_ok=True)
        dockerfile = svc_dir / "Dockerfile"
        dockerfile.write_text(_runner_dockerfile(), encoding="utf-8")
        task_sh = svc_dir / "run-task.sh"
        task_sh.write_text(run_script.read_text(encoding="utf-8"), encoding="utf-8")
        task_sh.chmod(0o755)
        generated_paths.append(svc_dir)

    profiles = list(dep.docker_profiles or ["autonomous-stack"])
    profile_str = ",".join(profiles)
    up_cmd = (
        f"docker compose -f docker-compose.yml -f examples/docker-compose.yml "
        f"-f {dep.stack_compose} --profile {profile_str} up -d"
    )

    manifest = gen_dir / "stack.manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "example_id": ex_id,
                "schedules": [s.model_dump() for s in ir.schedules],
                "deploy": dep.model_dump(),
                "generated_services": [s.model_dump() for s in ir.generated_services],
                "artifacts": {
                    "stack_compose": str(dep.stack_compose),
                    "ofelia_ini": str(ofelia_path.relative_to(ex_dir)),
                    "run_script": str(run_script.relative_to(ex_dir)),
                },
                "up_command": up_cmd,
                "validation_commands": [
                    f"test -f {dep.stack_compose}",
                    f"test -f {ofelia_path.relative_to(ex_dir)}",
                    f"grep -q '{dep.cron_service}' {dep.stack_compose}",
                ],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    return ComposeGenerationResult(
        stack_compose=stack_path,
        ofelia_ini=ofelia_path,
        run_script=run_script,
        manifest=manifest,
        generated_services=generated_paths,
        docker_profiles=profiles,
        up_command=up_cmd,
    )
