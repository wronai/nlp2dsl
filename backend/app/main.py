"""
MVP Automation Platform — Backend API

System kompilujący intencje biznesowe (deklaratywne DSL)
do wykonywalnych procesów (imperatywnych) w kontenerach Docker.
"""


from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_setup import RequestIDMiddleware, setup_logging
from app.routers.chat import router as chat_router
from app.routers.settings import router as settings_router
from app.routers.system import router as system_router
from app.routers.workflow import router as workflow_router

setup_logging(service="backend")

app = FastAPI(
    title="MVP Automation Platform",
    description=(
        "Platforma automatyzacji: deklaratywny DSL → imperatywne wykonanie w Docker.\n\n"
        "Użytkownik opisuje **co** chce zrobić (workflow DSL),\n"
        "system sam wie **jak** to wykonać (kontenery worker)."
    ),
    version="0.1.0",
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(system_router)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "backend"}
