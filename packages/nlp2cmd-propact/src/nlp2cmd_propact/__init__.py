"""Bridge nlp2cmd planning IR to Propact execution."""

from nlp2cmd_propact.adapter import plan_to_propact_markdown, step_to_propact_block
from nlp2cmd_propact.executor import HybridPlanExecutor, execution_route
from nlp2cmd_propact.runner import PropactRunner, RunResult

__all__ = [
    "HybridPlanExecutor",
    "PropactRunner",
    "RunResult",
    "execution_route",
    "plan_to_propact_markdown",
    "step_to_propact_block",
]

__version__ = "0.0.40"
