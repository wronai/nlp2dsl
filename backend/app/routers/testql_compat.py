"""
TestQL-compatible REST aliases for conversation E2E.

Maps /chatstart, /chatmessage, /runworkflow, /workflowfrom-text
to native nlp2dsl backend routes (used by testql ConversationRunner).
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engine import NLP_SERVICE_URL, run_workflow
from app.schemas import RunWorkflowRequest, Step

router = APIRouter(tags=["testql-compat"])

_EXECUTE_KEYWORDS = ("uruchom", "wykonaj", "start", "run", "ok", "tak", "go")


class TestqlChatStart(BaseModel):
    text: str | None = None
    message: str | None = None
    userId: str | None = None
    llmContext: dict[str, Any] | None = None
    llm_context: dict[str, Any] | None = None


class TestqlChatMessage(BaseModel):
    conversationId: str | None = None
    conversation_id: str | None = None
    text: str | None = None
    message: str | None = None
    llmContext: dict[str, Any] | None = None
    llm_context: dict[str, Any] | None = None


class TestqlRunWorkflow(BaseModel):
    conversationId: str | None = None
    conversation_id: str | None = None


def _alias_response(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    if "conversation_id" in out and "conversationId" not in out:
        out["conversationId"] = out["conversation_id"]
    return out


def _resolve_text(body: TestqlChatStart | TestqlChatMessage) -> str:
    text = getattr(body, "text", None) or getattr(body, "message", None) or ""
    llm_ctx = getattr(body, "llmContext", None) or getattr(body, "llm_context", None)
    if not text and llm_ctx:
        text = " ".join(f"{k}: {v}" for k, v in llm_ctx.items() if v is not None)
    return str(text).strip()


def _resolve_conv_id(body: TestqlChatMessage | TestqlRunWorkflow) -> str:
    cid = body.conversationId or body.conversation_id
    if not cid:
        raise HTTPException(status_code=422, detail="conversationId required")
    return str(cid)


async def _maybe_execute_on_message(result: dict[str, Any], text: str) -> dict[str, Any]:
    text_lower = text.lower()
    if result.get("status") == "ready" and any(kw in text_lower for kw in _EXECUTE_KEYWORDS):
        dsl = result.get("dsl")
        if dsl:
            req = RunWorkflowRequest(
                name=dsl.get("name", "chat_generated"),
                trigger=dsl.get("trigger", "manual"),
                steps=[Step(action=s["action"], config=s.get("config", {})) for s in dsl.get("steps", [])],
            )
            wf_result = await run_workflow(req)
            result = dict(result)
            result["status"] = "executed"
            result["execution"] = wf_result.model_dump()
            result["execution_backend"] = "worker"
    return result


@router.post("/chatstart")
async def testql_chatstart(body: TestqlChatStart) -> dict[str, Any]:
    text = _resolve_text(body)
    if not text:
        raise HTTPException(status_code=422, detail="text required for nlp2dsl chat start")
    llm_ctx = body.llmContext or body.llm_context
    data: dict[str, Any] = {"text": text}
    if llm_ctx:
        import json

        data["context_json"] = json.dumps(llm_ctx, ensure_ascii=False)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{NLP_SERVICE_URL}/chat/start", data=data)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return _alias_response(resp.json())


@router.post("/chatmessage")
async def testql_chatmessage(body: TestqlChatMessage) -> dict[str, Any]:
    conv_id = _resolve_conv_id(body)
    text = _resolve_text(body)
    llm_ctx = body.llmContext or body.llm_context
    data: dict[str, Any] = {"conversation_id": conv_id, "text": text}
    if llm_ctx:
        import json

        data["context_json"] = json.dumps(llm_ctx, ensure_ascii=False)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NLP_SERVICE_URL}/chat/message",
            data=data,
        )
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    result = await _maybe_execute_on_message(resp.json(), text)
    return _alias_response(result)


@router.post("/runworkflow")
async def testql_runworkflow(body: TestqlRunWorkflow) -> dict[str, Any]:
    conv_id = _resolve_conv_id(body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        state = await client.get(f"{NLP_SERVICE_URL}/chat/{conv_id}")
    if not state.is_success:
        raise HTTPException(status_code=state.status_code, detail=state.text)
    data = state.json()
    dsl = data.get("dsl")
    if not dsl:
        raise HTTPException(status_code=422, detail="conversation not ready — no DSL")
    req = RunWorkflowRequest(
        name=dsl.get("name", "chat_generated"),
        trigger=dsl.get("trigger", "manual"),
        steps=[Step(action=s["action"], config=s.get("config", {})) for s in dsl.get("steps", [])],
    )
    wf_result = await run_workflow(req)
    return _alias_response({
        "conversation_id": conv_id,
        "status": "executed",
        "execution": wf_result.model_dump(),
    })


@router.post("/workflowfrom-text")
async def testql_workflow_from_text(body: dict[str, Any]) -> dict[str, Any]:
    from app.routers.workflow import workflow_from_text

    return await workflow_from_text(body)
