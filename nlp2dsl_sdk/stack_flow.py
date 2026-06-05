"""
Autonomous stack orchestration — multi-turn validation + compose generation.

Combines:
  - DOQL registry bootstrap (environment.doql.less)
  - AutonomousFlow (server-side validation loop)
  - ConversationFlow (multi-turn when reflection reports gaps)
  - compose_generator (docker-compose + cron artifacts)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .autonomous_flow import AutonomousFlow
from .client import ConversationFlow, NLP2DSLClient
from .compose_generator import ComposeGenerationResult, enrich_ir_for_stack, generate_stack_compose
from .doql_context import load_doql_context
from .example_bootstrap import ensure_doql_registry
from .preview import execute_from_text
from .system_map_bridge import doql_file_to_system_map
from .system_map_generator import generate_system_map


@dataclass
class StackPhaseResult:
    name: str
    status: str
    detail: str = ""
    response: dict[str, Any] = field(default_factory=dict)


@dataclass
class StackRunResult:
    phases: list[StackPhaseResult] = field(default_factory=list)
    compose: ComposeGenerationResult | None = None
    registry_path: Path | None = None
    ok: bool = False


# Multi-turn prompts — each may trigger validation / reflection loop
DEFAULT_STACK_TURNS: tuple[tuple[str, str], ...] = (
    (
        "Zbuduj autonomiczny stack wysyłki faktur z harmonogramem codziennie o 9:00",
        "bootstrap",
    ),
    (
        "Wyślij fakturę do klient@firma.pl",
        "invoice_autonomous",
    ),
    (
        "Zaplanuj codziennie o 9:00 raport sprzedaży PDF i wyślij email do team@firma.pl",
        "schedule_validate",
    ),
)


class AutonomousStackFlow:
    """
    End-to-end: registry → autonomous execute → multi-turn validation → compose+cron emit.
    """

    def __init__(
        self,
        client: Optional[NLP2DSLClient] = None,
        *,
        example_dir: Path | str,
        reflect: bool = True,
        attachment: bool = True,
    ) -> None:
        self.client = client or NLP2DSLClient.from_env()
        self.example_dir = Path(example_dir).resolve()
        self.reflect = reflect
        self.attachment = attachment
        self._registry_path: Path | None = None

    def bootstrap_registry(self) -> Path:
        path = ensure_doql_registry(
            self.example_dir,
            attachment=self.attachment,
            auto_execute=True,
        )
        ir = generate_system_map(
            self.example_dir,
            example_id=self.example_dir.name,
            client=self.client,
        )
        ir.conversation.sync_auto_execute = True
        ir.conversation.attachment_required = self.attachment
        ir.conversation.generate_invoice_if_missing = True
        from .system_map_runtimes import load_example_profile

        profile = load_example_profile(self.example_dir.name, self.example_dir.parent.parent)
        ir = enrich_ir_for_stack(ir, example_id=self.example_dir.name, profile=profile)
        from .artifact_layout import write_registry
        from .system_map_render import render_system_map_doql

        write_registry(self.example_dir / ".nlp2dsl", render_system_map_doql(ir))
        self._registry_path = path
        return path

    def run_phases(
        self,
        turns: tuple[tuple[str, str], ...] | None = None,
    ) -> StackRunResult:
        os.environ.setdefault("NLP2DSL_EXAMPLE_DIR", str(self.example_dir))
        result = StackRunResult()
        turns = turns or DEFAULT_STACK_TURNS

        reg = self.bootstrap_registry()
        result.registry_path = reg
        print(f"📄 DOQL registry: {reg.relative_to(self.example_dir)}\n")

        for text, phase_name in turns:
            phase = self._run_phase(text, phase_name)
            result.phases.append(phase)
            icon = "✓" if phase.status in ("executed", "ready", "generated", "validated") else "✗"
            print(f"{icon} [{phase.name}] {phase.status}: {phase.detail}")

        compose = self._emit_compose()
        result.compose = compose
        result.phases.append(
            StackPhaseResult(
                name="compose_generate",
                status="generated",
                detail=str(compose.stack_compose.relative_to(self.example_dir)),
            )
        )
        print(f"\n📦 Stack compose: {compose.stack_compose.relative_to(self.example_dir)}")
        print(f"⏰ Cron config:   {compose.ofelia_ini.relative_to(self.example_dir)}")
        print(f"\n🚀 Uruchom stack:\n   {compose.up_command}")

        result.ok = (
            any(p.status == "executed" for p in result.phases)
            and result.compose is not None
            and result.compose.stack_compose.is_file()
        )
        return result

    def _run_phase(self, text: str, phase_name: str) -> StackPhaseResult:
        if phase_name == "bootstrap":
            return StackPhaseResult(
                name=phase_name,
                status="validated",
                detail="registry + SystemMapIR",
            )

        if phase_name == "invoice_autonomous":
            flow = AutonomousFlow(self.client, reflect=self.reflect)
            resp = flow.run_task(text)
            flow.save_artifacts(self.example_dir)
            status = str(resp.get("status", "unknown"))
            detail = f"autonomous_steps={resp.get('autonomous_steps', [])}"
            return StackPhaseResult(name=phase_name, status=status, detail=detail, response=resp)

        if phase_name == "schedule_validate":
            resp = execute_from_text(self.client, text, label="Harmonogram + walidacja DSL")
            status = str(resp.get("status", "unknown"))
            wf = resp.get("dsl") or {}
            trigger = wf.get("trigger", "?")
            return StackPhaseResult(
                name=phase_name,
                status=status,
                detail=f"trigger={trigger}",
                response=resp,
            )

        # Generic multi-turn with reflection loop
        conv = ConversationFlow(self.client, reflect=self.reflect)
        if not conv.conversation_id:
            resp = conv.start(text)
        else:
            resp = conv.send_message(text)
        conv.save_artifacts(self.example_dir)

        reflection = resp.get("reflection") or {}
        if reflection and not reflection.get("ready"):
            queries = reflection.get("context_queries") or []
            if queries:
                follow_up = conv.send_message(
                    f"Uzupełniam: {queries[0]} — klient@firma.pl, 1500 PLN, załącznik fixtures/faktura-2024.pdf"
                )
                resp = follow_up

        status = str(resp.get("status", "unknown"))
        return StackPhaseResult(name=phase_name, status=status, response=resp)

    def _emit_compose(self) -> ComposeGenerationResult:
        reg = self._registry_path
        if reg is None:
            reg = self.example_dir / ".nlp2dsl/registry/environment.doql.less"
        if reg.is_file():
            ir = doql_file_to_system_map(reg)
        else:
            ir = generate_system_map(self.example_dir, example_id=self.example_dir.name)
        from .system_map_runtimes import load_example_profile

        profile = load_example_profile(self.example_dir.name, self.example_dir.parent.parent)
        ir = enrich_ir_for_stack(ir, example_id=self.example_dir.name, profile=profile)
        result = generate_stack_compose(
            ir, example_dir=self.example_dir, profile=profile
        )
        from .artifact_layout import write_registry
        from .system_map_render import render_system_map_doql

        write_registry(self.example_dir / ".nlp2dsl", render_system_map_doql(ir))
        return result
