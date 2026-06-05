"""Conversation turn builders — unknown, system, DSL ready/incomplete, formatting."""

from __future__ import annotations

import json
import logging
import re
from typing import Callable

from app.dsl.forms import get_action_form
from app.dsl.pipeline import map_to_dsl_with_enrichment
from app.execution.system import SYSTEM_EXECUTORS
from app.execution.delegate import execution_backend_for_intent
from app.registry import SYSTEM_ACTIONS
from app.routing import IntentDecision
from app.schemas import (
    ConversationResponse,
    ConversationState,
    NLPEntities,
    NLPIntent,
    NLPResult,
)

log = logging.getLogger("orchestrator")

_SYSTEM_RESULT_PREVIEW_LENGTH: int = int("2000")
_SYSTEM_FILE_LIST_LIMIT: int = int("30")


def deny_message(decision: IntentDecision) -> str:
    if decision.deny_reason and decision.action:
        return (
            f"Brak uprawnień agenta `{decision.agent_id}` do `{decision.action}` "
            f"({decision.deny_effect}: {decision.deny_reason})."
        )
    return "Żądanie odrzucone."


_EXECUTE_KEYWORDS = (
    "uruchom",
    "wykonaj",
    "start",
    "run",
    "ok",
    "tak",
    "go",
    "kontynuuj",
    "continue",
    "dalej",
    "resume",
)


def _execute_keyword_in_text(text_lower: str, keyword: str) -> bool:
    """Match execute keywords; short tokens use word boundaries ('go' in 'zgodnie' → false)."""
    if " " in keyword:
        return keyword in text_lower
    if len(keyword) <= 4:
        return bool(re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text_lower))
    return keyword in text_lower


def _is_execute_or_continue(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(_execute_keyword_in_text(text_lower, kw) for kw in _EXECUTE_KEYWORDS)


async def check_execute_keyword(state: ConversationState, text: str) -> ConversationResponse | None:
    if not _is_execute_or_continue(text):
        return None
    if state.status == "ready" and state.dsl:
        log.info("Workflow already ready, preserving DSL for execution")
        return ConversationResponse(
            conversation_id=state.id,
            status="ready",
            message=(
                f"Workflow gotowy: {state.dsl.name} ({len(state.dsl.steps)} kroków). "
                "Wyślij 'uruchom' aby wykonać."
            ),
            dsl=state.dsl,
        )
    if state.intent and state.intent != "unknown" and state.status == "in_progress":
        return await build_incomplete_response(state)
    return None


def handle_unknown_intent(state: ConversationState) -> ConversationResponse | None:
    if not state.intent or state.intent == "unknown":
        if state.history and _is_execute_or_continue(
            state.history[-1].get("text", "")
        ):
            msg = (
                "Nie mam jeszcze rozpoczętego workflow w tej rozmowie. "
                "Podaj intencję (np. faktura, email) lub użyj komendy z Mullm "
                "(lista plikow usera, run ls -la)."
            )
            state.history.append({"role": "assistant", "text": msg})
            return ConversationResponse(
                conversation_id=state.id,
                status="in_progress",
                message=msg,
            )
        msg = (
            "Nie rozpoznałem intencji. Jaką automatyzację chcesz stworzyć?\n"
            "Np. faktura, raport, email, powiadomienie Slack.\n"
            "Komendy systemowe: ustawienia, pokaż pliki, status, pomoc."
        )
        state.history.append({"role": "assistant", "text": msg})
        return ConversationResponse(
            conversation_id=state.id,
            status="in_progress",
            message=msg,
        )
    return None


def handle_system_action(state: ConversationState) -> ConversationResponse | None:
    if state.intent not in SYSTEM_ACTIONS:
        return None

    config = {k: v for k, v in state.entities.items() if v is not None and k != "_trigger"}
    executor = SYSTEM_EXECUTORS.get(state.intent)
    if executor:
        try:
            inner_result = executor(config)
            result = {"action": state.intent, "status": "completed", "result": inner_result}
        except Exception as e:
            result = {"action": state.intent, "status": "failed", "error": str(e)}
    else:
        result = {"action": state.intent, "status": "failed", "error": "Executor not found"}

    state.status = "done"
    msg = format_system_result(state.intent, result)
    state.history.append({"role": "assistant", "text": msg})
    return ConversationResponse(
        conversation_id=state.id,
        status="done",
        message=msg,
        dsl=None,
    )


async def build_and_check_dsl(state: ConversationState) -> ConversationResponse | None:
    dialog = await map_to_dsl_with_enrichment(_nlp_from_state(state))
    if not (dialog.status == "complete" and dialog.workflow):
        return None

    state.dsl = dialog.workflow
    state.status = "ready"
    state.missing = []
    backend = execution_backend_for_intent(state.intent)
    msg = (
        f"Workflow gotowy: {dialog.workflow.name} ({len(dialog.workflow.steps)} kroków). "
        f"Wyślij 'uruchom' aby wykonać"
        + (" (Mullm)." if backend == "mullm" else ".")
    )
    state.history.append({"role": "assistant", "text": msg})
    return ConversationResponse(
        conversation_id=state.id,
        status="ready",
        message=msg,
        dsl=dialog.workflow,
        execution_backend=backend,
    )


async def build_incomplete_response(state: ConversationState) -> ConversationResponse:
    dialog = await map_to_dsl_with_enrichment(_nlp_from_state(state))
    state.missing = dialog.missing_fields
    question = dialog.prompt_user or "Podaj brakujące dane."

    form = None
    if dialog.missing_fields:
        first_missing_action = dialog.missing_fields[0].split(".")[0]
        form = get_action_form(first_missing_action)

    state.history.append({"role": "assistant", "text": question})
    return ConversationResponse(
        conversation_id=state.id,
        status="in_progress",
        message=question,
        missing=dialog.missing_fields,
        form=form,
    )


def _nlp_from_state(state: ConversationState) -> NLPResult:
    return NLPResult(
        intent=NLPIntent(intent=state.intent, confidence=1.0),
        entities=NLPEntities(**{k: v for k, v in state.entities.items() if k != "_trigger"}),
        raw_text=" ".join(h["text"] for h in state.history if h["role"] == "user"),
    )


def format_system_result(intent: str, result: dict) -> str:
    if result.get("status") == "failed":
        return f"Błąd: {result.get('error', 'nieznany')}"

    inner = result.get("result", result)
    formatter = _SYSTEM_RESULT_FORMATTERS.get(intent)
    if formatter:
        return formatter(inner)
    return json.dumps(inner, indent=2, ensure_ascii=False)


def _format_system_status(inner: dict) -> str:
    return (
        f"System v{inner.get('version', '?')}\n"
        f"LLM: {inner.get('llm_provider', '?')} / {inner.get('llm_model', '?')}\n"
        f"NLP: tryb {inner.get('nlp_mode', '?')}\n"
        f"Akcje: {inner.get('actions_business', 0)} biznesowych + "
        f"{inner.get('actions_system', 0)} systemowych"
    )


def _format_settings_get(inner: dict) -> str:
    settings = inner.get("settings", inner)
    return f"Ustawienia:\n{json.dumps(settings, indent=2, ensure_ascii=False)}"


def _format_settings_set(inner: dict) -> str:
    return f"Zmieniono {inner.get('path', '?')}: {inner.get('old', '?')} → {inner.get('new', '?')}"


def _format_settings_reset(inner: dict) -> str:
    return f"Ustawienia zresetowane: {inner.get('reset', 'all')}"


def _format_file_read(inner: dict) -> str:
    if inner.get("error"):
        return f"Błąd: {inner['error']}"
    return (
        f"Plik: {inner.get('file_path', '?')} "
        f"({inner.get('size_kb', '?')} KB, {inner.get('lines', '?')} linii)\n"
        f"---\n{inner.get('content', '')[:_SYSTEM_RESULT_PREVIEW_LENGTH]}"
    )


def _format_file_write(inner: dict) -> str:
    if inner.get("error"):
        return f"Błąd: {inner['error']}"
    return f"Zapisano: {inner.get('file_path', '?')} ({inner.get('size_kb', '?')} KB)"


def _format_file_list(inner: dict) -> str:
    files = inner.get("files", [])
    lines = [f"Pliki w {inner.get('directory', '?')} ({inner.get('count', 0)}):"]
    for file_info in files[:_SYSTEM_FILE_LIST_LIMIT]:
        lines.append(f"  {file_info['path']} ({file_info['size_kb']} KB)")
    return "\n".join(lines)


def _format_registry_list(inner: dict) -> str:
    actions = inner.get("actions", {})
    lines = [f"Zarejestrowane akcje ({inner.get('count', 0)}):"]
    for name, meta in actions.items():
        category = meta.get("category", "business")
        required = ", ".join(meta.get("required", []))
        description = meta["description"]
        lines.append(
            f"  [{category}] {name}: {description} "
            f"(required: {required or 'brak'})"
        )
    return "\n".join(lines)


def _format_registry_update(inner: dict) -> str:
    return f"Rejestr zaktualizowany: {json.dumps(inner, ensure_ascii=False)}"


_SYSTEM_RESULT_FORMATTERS: dict[str, Callable[[dict], str]] = {
    "system_status": _format_system_status,
    "system_settings_get": _format_settings_get,
    "system_settings_set": _format_settings_set,
    "system_settings_reset": _format_settings_reset,
    "system_file_read": _format_file_read,
    "system_file_write": _format_file_write,
    "system_file_list": _format_file_list,
    "system_registry_list": _format_registry_list,
    "system_registry_add": _format_registry_update,
    "system_registry_edit": _format_registry_update,
}
