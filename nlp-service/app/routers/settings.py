"""Settings API — /settings*."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from app.settings import settings_manager

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings() -> dict:
    """Pokaż wszystkie ustawienia systemu."""
    return {
        "settings": settings_manager.get_all(),
        "schema": settings_manager.describe(),
    }


@router.get("/settings/{section}")
async def get_settings_section(section: str) -> dict:
    """Pokaż ustawienia sekcji (llm, nlp, worker, file_access)."""
    data = settings_manager.get_section(section)
    if not data:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Section '{section}' not found")
    return {"section": section, "settings": data}


@router.put("/settings/{section}")
async def update_settings_section(section: str, body: dict) -> dict:
    """Zaktualizuj ustawienia sekcji."""
    try:
        return settings_manager.update_section(section, body)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e


@router.put("/settings")
async def set_setting(body: dict) -> dict:
    """Zmień pojedyncze ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}"""
    path = body.get("path", "")
    value = body.get("value")
    if not path:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Field 'path' is required")
    try:
        return settings_manager.set(path, value)
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e


@router.post("/settings/reset")
async def reset_settings(body: dict | None = None) -> dict:
    """Resetuj ustawienia. Body: {"section": "llm"} lub {} dla wszystkich."""
    payload = body or {}
    section = payload.get("section")
    return settings_manager.reset(section)
