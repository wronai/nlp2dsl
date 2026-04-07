"""
Settings router — /workflow/settings/*, /workflow/actions/schema/*.

Proxy do nlp-service settings i schema endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from app.engine import NLP_SERVICE_URL
from app.logging_setup import get_request_id

log = logging.getLogger("router.settings")
router = APIRouter(prefix="/workflow", tags=["settings"])


@router.get("/actions/schema")
async def actions_schema() -> dict[str, Any]:
    """Schematy formularzy UI — frontend generuje dynamicznie."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/actions/schema")
    return resp.json()


@router.get("/actions/schema/{action}")
async def action_schema(action: str) -> dict[str, Any]:
    """Schemat formularza dla konkretnej akcji."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/actions/schema/{action}")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    """Pokaż wszystkie ustawienia systemu."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/settings")
    return resp.json()


@router.get("/settings/{section}")
async def get_settings_section(section: str) -> dict[str, Any]:
    """Pokaż ustawienia sekcji."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.get(f"{NLP_SERVICE_URL}/settings/{section}")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.put("/settings/{section}")
async def update_settings_section(section: str, body: dict) -> dict[str, Any]:
    """Zaktualizuj ustawienia sekcji."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.put(f"{NLP_SERVICE_URL}/settings/{section}", json=body)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.put("/settings")
async def set_setting(body: dict) -> dict[str, Any]:
    """Zmień ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}"""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.put(f"{NLP_SERVICE_URL}/settings", json=body)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/settings/reset")
async def reset_settings(body: dict = {}) -> dict[str, Any]:
    """Resetuj ustawienia."""
    async with AsyncClient(timeout=10.0, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/settings/reset", json=body)
    return resp.json()
