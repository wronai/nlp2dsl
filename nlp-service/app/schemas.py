"""
Schematy NLP → DSL pipeline.

Trzy warstwy:
  1. NLPResult  — intent + entities (wyjście z LLM / parsera)
  2. WorkflowDSL — deterministyczny DSL (wyjście z mappera)
  3. DialogResponse — obsługa brakujących danych
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── NLP Output ────────────────────────────────────────────────

class NLPIntent(BaseModel):
    intent: str
    confidence: float = 1.0


class NLPEntities(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    to: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    channel: Optional[str] = None
    report_type: Optional[str] = None
    format: Optional[str] = None
    entity: Optional[str] = None
    data: Optional[dict] = None
    # ── System entities ──
    setting_path: Optional[str] = None      # np. "llm.model"
    setting_value: Optional[str] = None     # np. "gpt-4o-mini"
    section: Optional[str] = None           # np. "llm", "nlp", "worker"
    file_path: Optional[str] = None         # np. "worker/worker.py"
    content: Optional[str] = None           # treść pliku
    directory: Optional[str] = None         # katalog
    pattern: Optional[str] = None           # glob pattern
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    mode: Optional[str] = None              # "write" | "append"
    action_name: Optional[str] = None       # nazwa nowej akcji
    action_description: Optional[str] = None
    required_fields: Optional[list[str]] = None
    aliases: Optional[list[str]] = None


class NLPResult(BaseModel):
    intent: NLPIntent
    entities: NLPEntities = Field(default_factory=NLPEntities)
    missing: list[str] = []
    raw_text: str = ""


# ── DSL ───────────────────────────────────────────────────────

class DSLStep(BaseModel):
    action: str
    config: dict = {}


class WorkflowDSL(BaseModel):
    name: str
    trigger: Optional[str] = "manual"
    steps: list[DSLStep] = []


# ── Dialog (brakujące dane) ───────────────────────────────────

class DialogResponse(BaseModel):
    status: str  # "complete" | "incomplete"
    workflow: Optional[WorkflowDSL] = None
    missing_fields: list[str] = []
    prompt_user: Optional[str] = None  # pytanie do użytkownika


# ── Request ───────────────────────────────────────────────────

class NLPRequest(BaseModel):
    text: str
    context: dict = {}
    mode: str = "auto"  # "auto" | "llm" | "rules"


# ── Conversation State ───────────────────────────────────────

class ConversationState(BaseModel):
    """Stan rozmowy — akumuluje dane między turami dialogu."""
    id: str = ""
    intent: Optional[str] = None
    entities: dict = {}
    missing: list[str] = []
    dsl: Optional[WorkflowDSL] = None
    status: str = "in_progress"   # in_progress | ready | done | error
    history: list[dict] = []      # [{"role": "user"|"assistant", "text": "..."}]


# ── Schema-driven UI ─────────────────────────────────────────

class FieldSchema(BaseModel):
    name: str
    type: str = "string"     # string | number | email | select
    label: str = ""
    required: bool = True
    options: list[str] = []  # for select type
    default: Optional[str] = None


class ActionFormSchema(BaseModel):
    action: str
    description: str = ""
    fields: list[FieldSchema] = []


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str              # in_progress | ready | done
    message: Optional[str] = None
    dsl: Optional[WorkflowDSL] = None
    missing: list[str] = []
    form: Optional[ActionFormSchema] = None
