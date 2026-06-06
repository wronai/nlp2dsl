"""
NLP Service — pipeline: tekst → intent/entities → DSL.

Trzy tryby:
  - "rules" — offline, regex + aliasy (domyślny na MVP)
  - "llm"   — LLM API (OpenAI / Anthropic / Ollama)
  - "auto"  — rules first, LLM fallback jeśli confidence < 0.5
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_setup import RequestIDMiddleware, setup_logging
from app.routers.chat import router as chat_router
from app.routers.code import router as code_router
from app.routers.nlp import router as nlp_router
from app.routers.schema import router as schema_router
from app.routers.settings import router as settings_router
from app.routers.system import router as system_router
from app.routers.ws import router as ws_router

setup_logging(service="nlp-service")
log = logging.getLogger("nlp-service")

app = FastAPI(
    title="NLP → DSL Service",
    description=(
        "Pipeline NLP do automatyzacji:\n\n"
        "**LLM rozumie → Pydantic waliduje → Mapper buduje → Docker wykonuje**"
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

app.include_router(nlp_router)
app.include_router(chat_router)
app.include_router(schema_router)
app.include_router(settings_router)
app.include_router(system_router)
app.include_router(code_router)
app.include_router(ws_router)
