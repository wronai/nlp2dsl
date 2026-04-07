"""
System router — /workflow/system/execute.

Proxy do nlp-service system execution endpoint.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from app.engine import NLP_SERVICE_URL
from app.logging_setup import get_request_id

log = logging.getLogger("router.system")
router = APIRouter(prefix="/workflow", tags=["system"])

_PROXY_TIMEOUT_SECONDS: float = float("30.0")


@router.post("/system/execute")
async def system_execute(body: dict) -> dict[str, Any]:
    """Wykonaj akcję systemową. Body: {"action": "system_file_list", "config": {}}"""
    async with AsyncClient(timeout=_PROXY_TIMEOUT_SECONDS, headers={"X-Request-ID": get_request_id()}) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/system/execute", json=body)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
