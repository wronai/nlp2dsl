"""Attachment requirement checks for send_invoice workflows."""

from __future__ import annotations

from app.schemas import ConversationState, DialogResponse


def workflow_needs_attachment(state: ConversationState, dialog: DialogResponse) -> bool:
    if not state.attachment_required:
        return False
    workflow = dialog.workflow
    if not workflow:
        return True
    for step in workflow.steps:
        if step.action == "send_invoice":
            return not str(step.config.get("attachment_path", "")).strip()
    return False
