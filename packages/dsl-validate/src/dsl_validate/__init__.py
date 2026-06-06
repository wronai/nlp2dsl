"""Request validation pipeline — structured issues + legacy message bridge."""

from .context import ValidationContext
from .issue import Phase, Resolution, ValidationIssue, issues_to_messages
from .messages import legacy_message_to_issue
from .resolutions import (
    ResolutionEnvironment,
    ResolutionPlan,
    apply_resolution_plans,
    filter_plans_by_reflection_tokens,
    plan_resolutions,
)
from .profile_checks import (
    load_profile_validations,
    parse_profile_validation,
    parse_profile_validations,
    response_from_e2e_trace,
    run_profile_validation_checks,
    run_validations_from_raw,
    validate_profile_expectations,
)

_PIPELINE_EXPORTS = {
    "validate_dsl_contract_issues",
    "validate_dsl_contract_messages",
    "validate_post_execute_execution",
    "validate_post_execute_from_map",
    "validate_post_execute_issues",
    "validate_post_execute_workflow_from_map_issues",
    "validate_post_health_for_intent",
    "validate_post_health_from_map",
    "validate_post_health_issues",
    "validate_step_config_from_map",
    "validate_step_config_from_map_issues",
    "validate_step_issues",
    "validate_step_messages",
    "validate_workflow_from_map",
    "validate_workflow_from_map_issues",
}


def __getattr__(name: str):
    if name in _PIPELINE_EXPORTS:
        from . import pipeline

        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Phase",
    "Resolution",
    "ResolutionEnvironment",
    "ResolutionPlan",
    "ValidationContext",
    "ValidationIssue",
    "apply_resolution_plans",
    "filter_plans_by_reflection_tokens",
    "issues_to_messages",
    "legacy_message_to_issue",
    "plan_resolutions",
    "load_profile_validations",
    "parse_profile_validation",
    "parse_profile_validations",
    "response_from_e2e_trace",
    "run_profile_validation_checks",
    "run_validations_from_raw",
    "validate_profile_expectations",
    "validate_dsl_contract_issues",
    "validate_dsl_contract_messages",
    "validate_post_execute_execution",
    "validate_post_execute_from_map",
    "validate_post_execute_issues",
    "validate_post_execute_workflow_from_map_issues",
    "validate_post_health_for_intent",
    "validate_post_health_from_map",
    "validate_post_health_issues",
    "validate_step_config_from_map",
    "validate_step_config_from_map_issues",
    "validate_step_issues",
    "validate_step_messages",
    "validate_workflow_from_map",
    "validate_workflow_from_map_issues",
]
