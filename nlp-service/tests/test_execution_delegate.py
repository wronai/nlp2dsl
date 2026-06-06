"""Tests for execution/delegate.py."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from app.execution.delegate import (
    delegate_payload,
    execution_backend_for_intent,
    is_delegated_to_mullm,
)


def test_delegate_import_does_not_require_system_settings_dependency() -> None:
    root = Path(__file__).resolve().parents[1]
    repo_root = root.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root), str(repo_root), env.get("PYTHONPATH", "")]
    )
    code = textwrap.dedent(
        """
        import builtins

        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "pydantic_settings":
                raise ModuleNotFoundError("No module named 'pydantic_settings'")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        from app.execution.delegate import execution_backend_for_intent
        assert execution_backend_for_intent("send_invoice") == "worker"
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_mullm_shell_delegated() -> None:
    assert is_delegated_to_mullm("mullm_shell_task")
    assert execution_backend_for_intent("mullm_shell_task") == "mullm"


def test_invoice_worker_backend() -> None:
    assert execution_backend_for_intent("send_invoice") == "worker"


def test_system_runtime_backend() -> None:
    from app.conversation.doql_context import DoqlCommand, DoqlTaskContext
    from app.conversation.system_map import set_doql_context

    set_doql_context(
        DoqlTaskContext(
            commands=[DoqlCommand(name="system_file_list", runtime="orchestrator:nlp-service")],
        )
    )
    assert execution_backend_for_intent("system_file_list") == "system"
    set_doql_context(None)


def test_delegate_payload_shape() -> None:
    payload = delegate_payload("mullm_shell_task", {"shell_command": "ls"})
    assert payload["backend"] == "mullm"
    assert payload["action"] == "mullm_shell_task"
