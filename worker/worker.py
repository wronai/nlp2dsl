"""
Worker — warstwa imperatywna.

Wykonuje konkretne akcje (send_invoice, send_email, generate_report…)
wewnątrz kontenera Docker. Backend deleguje tu każdy krok workflow.

W produkcji: podmień simulate_* na prawdziwe integracje
(SMTP, API faktur, CRM SDK, Slack webhook itd.).
"""

import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from logging_setup import RequestIDMiddleware, setup_logging

setup_logging(service="worker")
log = logging.getLogger("worker")

app = FastAPI(title="Task Worker", version="0.1.0")
app.add_middleware(RequestIDMiddleware)


# ── Action registry ──────────────────────────────────────────

ACTION_HANDLERS = {}


def action(name: str):
    """Dekorator rejestrujący handler akcji."""
    def decorator(fn):
        ACTION_HANDLERS[name] = fn
        return fn
    return decorator


# ── Akcje (symulowane — MVP) ──────────────────────────────────


@action("send_invoice")
async def handle_send_invoice(config: dict) -> dict:
    log.info("⚡ Generating invoice → %s, amount: %s",
             config.get("to", "?"), config.get("amount", "?"))
    await asyncio.sleep(0.5)  # symulacja
    invoice_id = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    log.info("✅ Invoice %s created", invoice_id)
    return {"invoice_id": invoice_id, "sent_to": config.get("to")}


@action("send_email")
async def handle_send_email(config: dict) -> dict:
    log.info("📧 Sending email → %s, subject: '%s'",
             config.get("to", "?"), config.get("subject", "?"))
    await asyncio.sleep(0.3)
    log.info("✅ Email sent")
    return {"sent_to": config.get("to"), "subject": config.get("subject")}


@action("generate_report")
async def handle_generate_report(config: dict) -> dict:
    report_type = config.get("type", "sales")
    fmt = config.get("format", "pdf")
    log.info("📊 Generating %s report (%s)…", report_type, fmt)
    await asyncio.sleep(1.0)
    filename = f"report_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.{fmt}"
    log.info("✅ Report ready: %s", filename)
    return {"filename": filename, "type": report_type}


@action("crm_update")
async def handle_crm_update(config: dict) -> dict:
    entity = config.get("entity", "contact")
    log.info("🗃️ Updating CRM entity '%s'…", entity)
    await asyncio.sleep(0.4)
    log.info("✅ CRM updated")
    return {"entity": entity, "updated": True}


@action("notify_slack")
async def handle_notify_slack(config: dict) -> dict:
    channel = config.get("channel", "#general")
    log.info("💬 Sending Slack notification → %s", channel)
    await asyncio.sleep(0.2)
    log.info("✅ Slack message sent")
    return {"channel": channel, "delivered": True}


@action("generate_code")
async def handle_generate_code(config: dict) -> dict:
    import httpx

    description = config.get("description", "")
    language = config.get("language", "python")
    context = config.get("context")
    include_tests = config.get("include_tests", False)

    if not description:
        raise ValueError("Description is required for code generation")

    # Call nlp-service for code generation
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://nlp-service:8002/code/generate",
                json={
                    "description": description,
                    "language": language,
                    "context": context,
                    "include_tests": include_tests
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                log.error("Code generation failed: %s", result["error"])
                return {"error": result["error"], "language": language}

            log.info("✅ Generated %s code (%d lines)",
                    language, result.get("code", "").count("\n") + 1)
            return result

    except httpx.HTTPStatusError as e:
        log.error("HTTP error calling code generation: %s", e)
        return {"error": f"Code generation service unavailable: {e}"}
    except Exception as e:
        log.exception("Code generation failed")
        return {"error": str(e), "language": language}


# ── API endpoint ──────────────────────────────────────────────


@app.post("/execute")
async def execute_step(step: dict):
    """Wykonuje pojedynczy krok workflow."""
    step_id = step.get("step_id", "?")
    action_name = step.get("action")
    config = step.get("config", {})

    handler = ACTION_HANDLERS.get(action_name)
    if not handler:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: '{action_name}'. "
                   f"Available: {list(ACTION_HANDLERS.keys())}",
        )

    log.info("── Step [%s] action=%s ──", step_id, action_name)
    result = await handler(config)
    return {"step_id": step_id, "status": "completed", "result": result}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "worker", "actions": list(ACTION_HANDLERS.keys())}
