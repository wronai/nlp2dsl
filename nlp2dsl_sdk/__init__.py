"""Reusable SDK for working with NLP2DSL services.

The package import must stay lightweight. Service containers import submodules
such as ``nlp2dsl_sdk.validation`` and cannot safely import the HTTP client or
demo loader as a side effect.
"""

from .encoding import configure_utf8

configure_utf8()

_CLIENT_EXPORTS = {"ConversationFlow", "NLP2DSLClient", "workflow_step"}
_DEMO_EXPORTS = {
    "DEMO_REGISTRY",
    "DemoSpec",
    "list_available_demos",
    "run_action_catalog_demo",
    "run_automation_gallery_demo",
    "run_code_generation_demo",
    "run_crm_update_demo",
    "run_email_demo",
    "run_invoice_demo",
    "run_report_and_notify_demo",
    "run_scheduled_report_demo",
}


def __getattr__(name: str):
    if name in _CLIENT_EXPORTS:
        from . import client

        return getattr(client, name)
    if name in _DEMO_EXPORTS:
        from . import demos

        return getattr(demos, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ConversationFlow",
    "NLP2DSLClient",
    "DEMO_REGISTRY",
    "DemoSpec",
    "list_available_demos",
    "run_action_catalog_demo",
    "run_automation_gallery_demo",
    "run_code_generation_demo",
    "run_crm_update_demo",
    "run_email_demo",
    "run_invoice_demo",
    "run_report_and_notify_demo",
    "run_scheduled_report_demo",
    "workflow_step",
]
