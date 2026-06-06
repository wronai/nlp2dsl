"""Shared intent and execution-plan IR for nlp2cmd ↔ Propact."""

from pact_ir.execution_plan import ExecutionPlanIR, PlanStep
from pact_ir.intent import Ambiguity, EntityBag, IntentIR
from pact_ir.target_kind import ExecutionRisk, TargetKind

__all__ = [
    "Ambiguity",
    "EntityBag",
    "ExecutionPlanIR",
    "ExecutionRisk",
    "IntentIR",
    "PlanStep",
    "TargetKind",
]

__version__ = "0.0.36"
