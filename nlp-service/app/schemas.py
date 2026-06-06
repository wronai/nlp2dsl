"""
Schematy NLP → DSL pipeline.

Trzy warstwy:
  1. NLPResult  — intent + entities (wyjście z LLM / parsera)
  2. WorkflowDSL — deterministyczny DSL (wyjście z mappera)
  3. DialogResponse — obsługa brakujących danych
"""

from pydantic import BaseModel, Field

# ── NLP Output ────────────────────────────────────────────────

class NLPIntent(BaseModel):
    intent: str
    confidence: float = 1.0


class NLPEntities(BaseModel):
    amount: float | None = None
    currency: str | None = None
    to: str | None = None
    email_to: str | None = None  # drugi odbiorca (composite: faktura + email)
    subject: str | None = None
    message: str | None = None
    channel: str | None = None
    chat_id: str | None = None
    title: str | None = None
    report_type: str | None = None
    format: str | None = None
    entity: str | None = None
    data: dict | None = None
    # ── System entities ──
    setting_path: str | None = None      # np. "llm.model"
    setting_value: str | None = None     # np. "gpt-4o-mini"
    section: str | None = None           # np. "llm", "nlp", "worker"
    file_path: str | None = None         # np. "worker/worker.py"
    attachment_path: str | None = None   # plik faktury / załącznik
    content: str | None = None           # treść pliku
    directory: str | None = None         # katalog
    pattern: str | None = None           # glob pattern
    line_start: int | None = None
    line_end: int | None = None
    mode: str | None = None              # "write" | "append"
    action_name: str | None = None       # nazwa nowej akcji
    action_description: str | None = None
    required_fields: list[str] | None = None
    aliases: list[str] | None = None
    # ── Code generation ──
    description: str | None = None
    language: str | None = None
    context: str | None = None
    include_tests: bool | None = None
    # ── Mullm / delegated ──
    shell_command: str | None = None


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
    trigger: str | None = "manual"
    steps: list[DSLStep] = []


# ── Dialog (brakujące dane) ───────────────────────────────────

class DialogResponse(BaseModel):
    status: str  # "complete" | "incomplete"
    workflow: WorkflowDSL | None = None
    missing_fields: list[str] = []
    prompt_user: str | None = None  # pytanie do użytkownika


# ── Request ───────────────────────────────────────────────────

class NLPRequest(BaseModel):
    text: str
    context: dict = {}
    mode: str = "auto"  # "auto" | "llm" | "rules"


class OrientRequest(BaseModel):
    text: str
    connector: str = "mullm"  # mullm | local


# ── Conversation State ───────────────────────────────────────

class ConversationState(BaseModel):
    """Stan rozmowy — akumuluje dane między turami dialogu."""
    id: str = ""
    intent: str | None = None
    entities: dict = {}
    missing: list[str] = []
    dsl: WorkflowDSL | None = None
    status: str = "in_progress"   # in_progress | ready | executed | done | error
    history: list[dict] = []      # [{"role": "user"|"assistant", "text": "..."}]
    doql_context_path: str | None = None
    doql_inline: dict = {}
    autofill_applied: list[str] = []
    attachment_required: bool = False
    autonomous_steps: list[str] = []
    execution: dict | None = None


# ── Schema-driven UI ─────────────────────────────────────────

class FieldSchema(BaseModel):
    name: str
    type: str = "string"     # string | number | email | select
    label: str = ""
    required: bool = True
    options: list[str] = []  # for select type
    default: str | None = None


class ActionFormSchema(BaseModel):
    action: str
    description: str = ""
    fields: list[FieldSchema] = []


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str              # in_progress | ready | done
    message: str | None = None
    dsl: WorkflowDSL | None = None
    missing: list[str] = []
    form: ActionFormSchema | None = None
    execution_backend: str | None = None  # worker | mullm | system
    routing: dict | None = None  # IntentDecision — debug / Mullm ingress trace
    autofill_applied: list[str] = []
    reflection: dict | None = None  # ReflectionReport — target vs current after each decision
    autonomous_steps: list[str] = []
    auto_execute: bool = False
    execution: dict | None = None
    attachment_validation: dict | None = None
