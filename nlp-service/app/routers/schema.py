"""Schema-driven UI endpoints — /actions/schema*."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from app.conversation.system_map import known_action_names
from app.orchestrator import get_action_form
from app.schemas import ActionFormSchema

router = APIRouter(tags=["schema"])


@router.get("/actions/schema")
async def actions_schema() -> dict:
    """Pełny schemat formularzy dla wszystkich akcji."""
    schemas = {}
    for action_name in sorted(known_action_names()):
        form = get_action_form(action_name)
        if form:
            schemas[action_name] = form.model_dump()
    return schemas


@router.get("/actions/schema/{action}", response_model=ActionFormSchema)
async def action_schema(action: str) -> ActionFormSchema:
    """Schemat formularza dla konkretnej akcji."""
    form = get_action_form(action)
    if not form:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Action '{action}' not found")
    return form
