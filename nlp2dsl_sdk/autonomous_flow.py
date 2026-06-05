"""Autonomous conversation — one task in, validate/resolve/execute out."""

from __future__ import annotations

import os
from typing import Any, Optional

from .client import ConversationFlow, NLP2DSLClient


class AutonomousFlow(ConversationFlow):
    """
    Single-shot task runner with server-side autonomous resolution loop.

    With sync_auto_execute in DOQL (or auto_execute=True), backend runs workflow
    after the first chat/start without manual 'uruchom'.
    """

    def __init__(
        self,
        client: Optional[NLP2DSLClient] = None,
        *,
        auto_execute: bool | None = None,
        reflect: bool = True,
    ) -> None:
        super().__init__(client, reflect=reflect)
        self.auto_execute = auto_execute
        self.autonomous_steps: list[str] = []

    def run_task(self, text: str, *, audio_path: Optional[str] = None) -> dict[str, Any]:
        """Submit task; server autonomously fills gaps and optionally executes."""
        os.environ.setdefault("NLP2DSL_EXAMPLE_DIR", str(self._default_example_dir()))

        extra: dict[str, Any] = {}
        if self._should_auto_execute():
            extra["sync_auto_execute"] = True
            extra["auto_execute"] = True

        data = self._start_with_extra(text, audio_path=audio_path, extra=extra)
        self.autonomous_steps = list(data.get("autonomous_steps") or [])

        if data.get("status") == "ready" and self._should_auto_execute():
            data = self.send_message("uruchom")
        elif data.get("status") != "executed" and self._should_auto_execute():
            # backend may not have auto-ran; explicit execute turn
            if data.get("auto_execute"):
                data = self.send_message("uruchom")

        return data

    def _should_auto_execute(self) -> bool:
        if self.auto_execute is not None:
            return self.auto_execute
        return os.environ.get("NLP2DSL_AUTO_EXECUTE", "1").strip().lower() in ("1", "true", "yes")

    def _default_example_dir(self) -> str:
        return os.environ.get("NLP2DSL_EXAMPLE_DIR", ".")

    def _start_with_extra(
        self,
        text: str,
        *,
        audio_path: Optional[str] = None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        import json
        from pathlib import Path

        from .artifact_layout import current_run_id, ensure_layout
        from .doql_context import load_doql_inline_from_env, resolve_doql_context_path

        example_dir = os.environ.get("NLP2DSL_EXAMPLE_DIR", "").strip()
        if example_dir:
            ensure_layout(Path(example_dir) / ".nlp2dsl")
            self._run_id = current_run_id(Path(example_dir) / ".nlp2dsl")
        self._turn_index = 0
        print(f"👤 Zadanie: {text}")

        inline = dict(load_doql_inline_from_env() or {})
        inline.update(extra)
        payload: dict[str, Any] = {"text": text}
        if inline:
            payload["context_json"] = json.dumps(inline, ensure_ascii=False)
        doql_path = resolve_doql_context_path()
        if doql_path:
            payload["doql_context_path"] = str(doql_path)

        if audio_path:
            path = Path(audio_path)
            with path.open("rb") as audio_file:
                response = self.client._backend(
                    "post",
                    "/workflow/chat/start",
                    data=payload,
                    files={"audio": (path.name, audio_file, "application/octet-stream")},
                )
            data = response.json()
        else:
            data = self.client._backend("post", "/workflow/chat/start", json=payload).json()

        self.conversation_id = data["conversation_id"]
        self.history.append({"role": "user", "text": text})
        self._record_turn("user", text, "/workflow/chat/start", data)
        self._handle_response(data)
        return data
