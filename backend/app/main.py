"""
MVP Automation Platform — Backend API

System kompilujący intencje biznesowe (deklaratywne DSL)
do wykonywalnych procesów (imperatywnych) w kontenerach Docker.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.workflow import router as workflow_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
)

app = FastAPI(
    title="MVP Automation Platform",
    description=(
        "Platforma automatyzacji: deklaratywny DSL → imperatywne wykonanie w Docker.\n\n"
        "Użytkownik opisuje **co** chce zrobić (workflow DSL),\n"
        "system sam wie **jak** to wykonać (kontenery worker)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend"}
