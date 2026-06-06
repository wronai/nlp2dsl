"""System action execution — /system/execute."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from app.system_executor import SYSTEM_EXECUTORS, execute_system_action

router = APIRouter(tags=["system"])


@router.post("/system/execute")
async def system_execute(body: dict) -> dict:
    """Wykonaj akcję systemową bezpośrednio."""
    action = body.get("action", "")
    config = body.get("config", {})

    if action not in SYSTEM_EXECUTORS:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Unknown system action: '{action}'. Available: {list(SYSTEM_EXECUTORS.keys())}",
        )

    return await execute_system_action(action, config)
