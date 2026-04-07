"""Reusable SDK for working with NLP2DSL services."""

from .client import ConversationFlow, NLP2DSLClient, workflow_step
from .demos import (
    DEMO_REGISTRY,
    DemoSpec,
    list_available_demos,
    run_action_catalog_demo,
    run_automation_gallery_demo,
    run_code_generation_demo,
    run_crm_update_demo,
    run_email_demo,
    run_invoice_demo,
    run_report_and_notify_demo,
    run_scheduled_report_demo,
)

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
