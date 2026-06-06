"""
Generate docker-compose stack + cron artifacts from SystemMapIR / DOQL registry.

Output under `.nlp2dsl/generated/`:
  - docker-compose.stack.yaml
  - crontab (cron scheduler)
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

from env2llm.ir import DeploySpecIR, GeneratedServiceIR, ScheduleSpecIR, SystemMapIR
from env2llm.runtimes import load_example_profile


@dataclass
class ComposeGenerationResult:
    stack_compose: Path
    crontab: Path
    run_script: Path
    manifest: Path
    up_script: Path | None = None
    generated_services: list[Path] = field(default_factory=list)
    docker_profiles: list[str] = field(default_factory=list)
    up_command: str = ""


def _default_deploy(example_id: str, profile: dict[str, Any] | None) -> DeploySpecIR:
    return DeploySpecIR(
        docker_profiles=["autonomous-stack"],
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


def _wait_for_backend_shell(*, max_var: str = "NLP2DSL_BACKEND_WAIT") -> str:
    return textwrap.dedent(
        f"""\
        _wait_for_backend() {{
          max="${{{max_var}:-30}}"
          i=0
          while [ "$i" -lt "$max" ]; do
            if curl -sf "$BACKEND/health" >/dev/null 2>&1; then
              return 0
            fi
            i=$((i + 1))
            sleep 1
          done
          echo "[process] backend not ready at $BACKEND (waited ${{max}}s)"
          return 1
        }}
        """
    )


def _run_script_content(*, backend_url: str, task: str, in_docker: bool = False) -> str:
    """Layer 2 — process dispatch via curl (works in cron container or on host)."""
    safe_task = task.replace('"', '\\"')
    default_backend = "http://backend:8000" if in_docker else backend_url
    return textwrap.dedent(
        f"""\
        #!/bin/sh
        # Layer 2: wykonanie procesu (curl → backend/workflow/run)
        # Layer 1 (platforma) musi już działać: docker compose up -d
        set -eu
        BACKEND="${{NLP2DSL_BACKEND_URL:-{default_backend}}}"
        echo "[process] $(date -Iseconds) task={safe_task!r} backend=$BACKEND"
        {_wait_for_backend_shell()}
        _wait_for_backend || {{ echo "[process] FAILED — uruchom Layer 1: docker compose up -d"; exit 1; }}
        curl -sf -X POST "$BACKEND/workflow/run" \\
          -H "Content-Type: application/json" \\
          -d '{{"name":"scheduled_stack","trigger":"cron","steps":[{{"action":"send_invoice","config":{{"amount":1500,"to":"klient@firma.pl","currency":"PLN"}}}}]}}' \\
          || {{ echo "[process] FAILED — uruchom Layer 1: docker compose up -d"; exit 1; }}
        echo "[process] OK"
        """
    )


def _run_process_host_script(*, backend_url: str, task: str) -> str:
    return _run_script_content(backend_url=backend_url, task=task, in_docker=False)


def _run_process_docker_script(*, task: str) -> str:
    return _run_script_content(backend_url="http://backend:8000", task=task, in_docker=True)


def _up_platform_script(repo_root: Path) -> str:
    return textwrap.dedent(
        f"""\
        #!/bin/sh
        # Layer 1 — infrastruktura NLP2DSL (backend, nlp-service, worker, postgres, redis)
        set -eu
        cd "{repo_root}"
        PORT="${{NLP2DSL_BACKEND_HOST_PORT:-8010}}"
        echo "[platform] docker compose up -d ..."
        docker compose -f docker-compose.yml up -d "$@"
        echo "[platform] waiting for backend on :$PORT ..."
        max="${{NLP2DSL_BACKEND_WAIT:-30}}"
        i=0
        while [ "$i" -lt "$max" ]; do
          if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
            echo "[platform] backend ready"
            exit 0
          fi
          i=$((i + 1))
          sleep 1
        done
        echo "[platform] WARN: backend not responding yet — retry run-process.sh shortly"
        exit 0
        """
    )


def _run_process_wrapper_script(repo_root: Path, stack_rel: Path) -> str:
    return textwrap.dedent(
        f"""\
        #!/bin/sh
        # Layer 2 — proces w sieci Docker (curl w jednorazowym kontenerze)
        set -eu
        cd "{repo_root}"
        exec docker compose -f docker-compose.yml -f {stack_rel} \\
          --profile autonomous-stack run --rm process-shell "$@"
        """
    )


def _process_shell_dockerfile() -> str:
    return textwrap.dedent(
        """\
        FROM alpine:3.20
        RUN apk add --no-cache curl bash
        COPY run-process.sh /run-process.sh
        RUN chmod +x /run-process.sh
        ENTRYPOINT ["sh", "/run-process.sh"]
        """
    )


def _cron_sidecar_dockerfile() -> str:
    return textwrap.dedent(
        """\
        FROM alpine:3.20
        RUN apk add --no-cache curl bash dcron
        COPY run-process.sh /task.sh
        COPY crontab /etc/crontabs/root
        RUN chmod +x /task.sh
        CMD ["crond", "-f", "-l", "2"]
        """
    )


def _crontab_content(schedules: list[ScheduleSpecIR]) -> str:
    lines: list[str] = []
    for sched in schedules:
        if sched.enabled:
            lines.append(f"{sched.cron} /task.sh # {sched.id}")
    if not lines:
        lines.append("0 9 * * * /task.sh # daily-invoice")
    return "\n".join(lines) + "\n"


def _stack_compose_dict(
    ir: SystemMapIR,
    *,
    example_id: str,
    example_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    dep = ir.deploy or _default_deploy(example_id, None)
    profiles = dep.docker_profiles or ["autonomous-stack"]
    gen_rel = Path(dep.stack_compose).parent
    try:
        ex_rel = example_dir.relative_to(repo_root)
    except ValueError:
        ex_rel = Path(example_dir.name)
    vol_base = ex_rel / gen_rel
    build_base = vol_base / "services"

    services: dict[str, Any] = {
        dep.cron_service: {
            "build": {"context": str(build_base / "stack-cron")},
            "profiles": profiles,
            "depends_on": ["backend"],
            "environment": ["NLP2DSL_BACKEND_URL=http://backend:8000"],
            "labels": {
                "nlp2dsl.layer": "scheduler",
                "nlp2dsl.example": example_id,
            },
        },
        "process-shell": {
            "build": {"context": str(build_base / "process-shell")},
            "profiles": profiles,
            "depends_on": ["backend"],
            "environment": ["NLP2DSL_BACKEND_URL=http://backend:8000"],
            "labels": {"nlp2dsl.layer": "process"},
            "restart": "no",
        },
    }

    for svc in ir.generated_services:
        if svc.build_context:
            svc_folder = svc.build_context.split("/")[-1]
            rel_build = str(build_base / svc_folder)
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

    cron_name = dep.cron_service
    runner_names = [s.name for s in ir.generated_services]

    return {
        "services": services,
        "x-nlp2dsl": {
            "example_id": example_id,
            "project": "nlp2dsl",
            "example_dir": str(example_dir),
            "repo_root": str(repo_root),
            "platform_compose": dep.platform_compose,
            "mocks_compose": dep.mocks_compose,
            "docker_profiles": profiles,
            "stack_services": [cron_name, "process-shell", *runner_names],
            "layers": {
                "infrastructure": {
                    "compose": dep.platform_compose,
                    "services": ["backend", "nlp-service", "worker", "postgres", "redis"],
                    "up": f"docker compose -f {dep.platform_compose} up -d",
                },
                "process": {
                    "tools": ["curl", "sh"],
                    "host_script": f"{gen_rel}/run-process.sh",
                    "docker_script": f"{gen_rel}/run-process-docker.sh",
                    "in_docker": (
                        f"docker compose -f {dep.platform_compose} -f {ex_rel / dep.stack_compose} "
                        f"--profile autonomous-stack run --rm process-shell"
                    ),
                    "on_host": f"sh {ex_rel / gen_rel}/run-process.sh",
                },
                "scheduler": {
                    "service": cron_name,
                    "cron_config": f"{gen_rel}/crontab",
                    "profile": "autonomous-stack",
                },
            },
            "includes": [
                f"docker compose -f {dep.platform_compose} up -d",
                f"docker compose -f {dep.platform_compose} -f {ex_rel / dep.stack_compose} "
                f"--profile autonomous-stack up -d {cron_name}",
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

    task_text = ir.schedules[0].task if ir.schedules else "Wyślij fakturę"

    run_host = gen_dir / "run-process.sh"
    run_host.write_text(
        _run_process_host_script(backend_url="http://localhost:8010", task=task_text),
        encoding="utf-8",
    )
    run_host.chmod(0o755)

    run_docker = gen_dir / "run-process-docker.sh"
    run_docker.write_text(_run_process_docker_script(task=task_text), encoding="utf-8")
    run_docker.chmod(0o755)

    shell_dir = gen_dir / "services" / "process-shell"
    shell_dir.mkdir(parents=True, exist_ok=True)
    (shell_dir / "Dockerfile").write_text(_process_shell_dockerfile(), encoding="utf-8")
    (shell_dir / "run-process.sh").write_text(run_docker.read_text(encoding="utf-8"), encoding="utf-8")
    (shell_dir / "run-process.sh").chmod(0o755)

    cron_dir = gen_dir / "services" / "stack-cron"
    cron_dir.mkdir(parents=True, exist_ok=True)
    (cron_dir / "Dockerfile").write_text(_cron_sidecar_dockerfile(), encoding="utf-8")
    (cron_dir / "run-process.sh").write_text(run_docker.read_text(encoding="utf-8"), encoding="utf-8")
    (cron_dir / "run-process.sh").chmod(0o755)
    (cron_dir / "crontab").write_text(_crontab_content(ir.schedules), encoding="utf-8")

    # legacy alias
    run_script = gen_dir / "run-scheduled-task.sh"
    run_script.write_text(run_host.read_text(encoding="utf-8"), encoding="utf-8")
    run_script.chmod(0o755)

    crontab_path = gen_dir / "crontab"
    crontab_path.write_text(_crontab_content(ir.schedules), encoding="utf-8")

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
        task_sh.write_text(run_docker.read_text(encoding="utf-8"), encoding="utf-8")
        task_sh.chmod(0o755)
        generated_paths.append(svc_dir)

    profiles = list(dep.docker_profiles or ["autonomous-stack"])
    try:
        stack_rel = ex_dir.relative_to(root) / dep.stack_compose
        ex_rel = ex_dir.relative_to(root)
    except ValueError:
        stack_rel = Path(dep.stack_compose)
        ex_rel = Path(ex_id)
    gen_rel = Path(".nlp2dsl") / "generated"
    cron_name = dep.cron_service
    runner_names = [s.name for s in ir.generated_services]
    stack_services = " ".join([cron_name, *runner_names])

    profile_flags = "--profile autonomous-stack"
    up_cmd = (
        f"cd {root} && docker compose -f docker-compose.yml -f {stack_rel} "
        f"{profile_flags} up -d {stack_services}"
    )
    mocks_cmd = (
        f"cd {root} && docker compose -f examples/docker-compose.yml "
        f"--profile invoice up -d smtp-mock"
    )

    up_platform = gen_dir / "up-platform.sh"
    up_platform.write_text(_up_platform_script(root), encoding="utf-8")
    up_platform.chmod(0o755)

    run_in_docker = gen_dir / "run-process-in-docker.sh"
    run_in_docker.write_text(_run_process_wrapper_script(root, stack_rel), encoding="utf-8")
    run_in_docker.chmod(0o755)

    up_script = gen_dir / "up-stack.sh"
    up_script.write_text(
        f"""#!/bin/sh
set -eu
ROOT="{root}"
STACK="{stack_rel}"
CRON="{cron_name}"

cd "$ROOT"

# ── Layer 1: infrastruktura NLP2DSL ─────────────────────────────
if ! docker compose -f docker-compose.yml ps --status running -q backend 2>/dev/null | grep -q .; then
  echo "[Layer 1] Platform: docker compose up -d"
  docker compose -f docker-compose.yml up -d
else
  echo "[Layer 1] Platform already running"
fi

docker compose -f examples/docker-compose.yml --profile invoice up -d smtp-mock 2>/dev/null || true

# ── Layer 2 (scheduled): cron wywołuje curl w sieci Docker ───────
echo "[Layer 2] Scheduler: $CRON (dcron + curl → backend:8000)"
exec docker compose -f docker-compose.yml -f "$STACK" --profile autonomous-stack up -d "$CRON" "$@"
""",
        encoding="utf-8",
    )
    up_script.chmod(0o755)

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
                    "crontab": str(crontab_path.relative_to(ex_dir)),
                    "run_process_host": str(run_host.relative_to(ex_dir)),
                    "run_process_docker": str(run_docker.relative_to(ex_dir)),
                    "up_platform": str(up_platform.relative_to(ex_dir)),
                },
                "layers": {
                    "1_infrastructure": "up-platform.sh → docker-compose.yml",
                    "2_process_host": "run-process.sh → curl localhost:8010",
                    "2_process_docker": "run-process-in-docker.sh → curl backend:8000",
                    "2_process_scheduled": f"{cron_name} + crontab",
                },
                "up_platform_command": f"cd {root} && sh {ex_rel / gen_rel / 'up-platform.sh'}",
                "run_process_command": f"sh {ex_rel / gen_rel / 'run-process.sh'}",
                "run_process_in_docker_command": (
                    f"cd {root} && docker compose -f docker-compose.yml -f {stack_rel} "
                    f"--profile autonomous-stack run --rm process-shell"
                ),
                "up_command": up_cmd,
                "mocks_command": mocks_cmd,
                "up_script": str(up_script.relative_to(ex_dir)),
                "validation_commands": [
                    f"test -f {dep.stack_compose}",
                    f"test -f {crontab_path.relative_to(ex_dir)}",
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
        crontab=crontab_path,
        run_script=run_script,
        manifest=manifest,
        up_script=up_script,
        generated_services=generated_paths,
        docker_profiles=profiles,
        up_command=up_cmd,
    )
