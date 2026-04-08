"""
Tests for nlp-service/app/system_executor.py — system action handlers.

Tests settings get/set/reset, file listing, registry list/add.
Uses SettingsManager singleton (reset per test).
"""

from __future__ import annotations

import pytest
from app.registry import ACTIONS_REGISTRY
from app.settings import SystemSettings, settings_manager
from app.system_executor import (
    SYSTEM_EXECUTORS,
    _exec_file_list,
    _exec_registry_add,
    _exec_registry_list,
    _exec_settings_get,
    _exec_settings_reset,
    _exec_settings_set,
    _exec_status,
)


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    """Reset settings to defaults before each test. Disable file persistence."""
    settings_manager._settings = SystemSettings()
    monkeypatch.setattr(settings_manager, "_save", lambda: None)
    yield
    settings_manager._settings = SystemSettings()


# ── Settings get ─────────────────────────────────────────────────


class TestSettingsGet:
    """_exec_settings_get handler."""

    def test_settings_get_all(self) -> None:
        """Get all settings → returns dict with 'settings' key."""
        result = _exec_settings_get({"section": "all"})
        assert "settings" in result
        assert "llm" in result["settings"]
        assert "nlp" in result["settings"]
        assert "worker" in result["settings"]

    def test_settings_get_section(self) -> None:
        """Get specific section → returns only that section."""
        result = _exec_settings_get({"section": "llm"})
        assert result["section"] == "llm"
        assert "model" in result["settings"]

    def test_settings_get_default_is_all(self) -> None:
        """No section specified → defaults to 'all'."""
        result = _exec_settings_get({})
        assert "settings" in result


# ── Settings set ─────────────────────────────────────────────────


class TestSettingsSet:
    """_exec_settings_set handler."""

    def test_settings_set_and_verify(self) -> None:
        """Set llm.temperature → value changes."""
        result = _exec_settings_set({
            "setting_path": "llm.temperature",
            "setting_value": "0.7",
        })
        assert result["path"] == "llm.temperature"
        assert result["new"] == 0.7
        # Verify via get
        assert settings_manager.get("llm.temperature") == 0.7

    def test_settings_set_missing_path(self) -> None:
        """Missing setting_path → error."""
        result = _exec_settings_set({"setting_value": "0.5"})
        assert "error" in result

    def test_settings_set_missing_value(self) -> None:
        """Missing setting_value → error."""
        result = _exec_settings_set({"setting_path": "llm.temperature"})
        assert "error" in result


# ── Settings reset ───────────────────────────────────────────────


class TestSettingsReset:
    """_exec_settings_reset handler."""

    def test_settings_reset(self) -> None:
        """Reset all settings → back to defaults."""
        # Change something first
        settings_manager.set("llm.temperature", 0.9)
        assert settings_manager.get("llm.temperature") == 0.9

        result = _exec_settings_reset({})
        assert result["reset"] == "all"
        assert settings_manager.get("llm.temperature") == 0.0

    def test_settings_reset_section(self) -> None:
        """Reset specific section only."""
        settings_manager.set("llm.temperature", 0.5)
        result = _exec_settings_reset({"section": "llm"})
        assert result["reset"] == "llm"
        assert settings_manager.get("llm.temperature") == 0.0


# ── File list ────────────────────────────────────────────────────


class TestFileList:
    """_exec_file_list handler."""

    def test_file_list(self, tmp_path, monkeypatch) -> None:
        """List files in temp directory → returns files list."""
        # Create test files
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.py").write_text("print()")
        # Allow access to tmp_path
        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        result = _exec_file_list({"directory": str(tmp_path)})
        assert "files" in result
        assert "count" in result
        assert isinstance(result["files"], list)
        assert result["count"] == 2

    def test_file_list_nonexistent(self) -> None:
        """Non-existent directory → error."""
        result = _exec_file_list({"directory": "/nonexistent/path/xyz"})
        assert "error" in result


# ── Registry list ────────────────────────────────────────────────


class TestRegistryList:
    """_exec_registry_list handler."""

    def test_registry_list(self) -> None:
        """List all actions → returns actions dict."""
        result = _exec_registry_list({"category": "all"})
        assert "actions" in result
        assert "count" in result
        assert result["count"] > 0
        assert "send_invoice" in result["actions"]

    def test_registry_list_business(self) -> None:
        """List business-only actions."""
        result = _exec_registry_list({"category": "business"})
        for name, meta in result["actions"].items():
            assert meta["category"] == "business"

    def test_registry_list_system(self) -> None:
        """List system-only actions."""
        result = _exec_registry_list({"category": "system"})
        for name, meta in result["actions"].items():
            assert meta["category"] == "system"


# ── Registry add ─────────────────────────────────────────────────


class TestRegistryAdd:
    """_exec_registry_add handler."""

    def test_registry_add(self) -> None:
        """Add a new action → appears in registry."""
        test_name = "_test_action_add"
        # Clean up if left from previous run
        ACTIONS_REGISTRY.pop(test_name, None)

        result = _exec_registry_add({
            "action_name": test_name,
            "action_description": "Test action",
            "required_fields": "field1, field2",
            "aliases": "test, testuj",
        })
        assert result.get("added") == test_name
        assert test_name in ACTIONS_REGISTRY

        # Clean up
        ACTIONS_REGISTRY.pop(test_name, None)

    def test_registry_add_missing_name(self) -> None:
        """Add without action_name → error."""
        result = _exec_registry_add({"action_description": "No name"})
        assert "error" in result

    def test_registry_add_duplicate(self) -> None:
        """Add existing action → error."""
        result = _exec_registry_add({
            "action_name": "send_invoice",
            "action_description": "Duplicate",
        })
        assert "error" in result


# ── Status ───────────────────────────────────────────────────────


class TestStatus:
    """_exec_status handler."""

    def test_status(self) -> None:
        """System status returns expected fields."""
        result = _exec_status({})
        assert "version" in result
        assert "llm_model" in result
        assert "nlp_mode" in result
        assert "actions_total" in result
        assert "actions_business" in result
        assert "actions_system" in result


# ── Registry edit ────────────────────────────────────────────────


class TestRegistryEdit:
    """_exec_registry_edit handler."""

    def test_registry_edit_description(self) -> None:
        """Edit an existing action's description."""
        from app.system_executor import _exec_registry_edit

        test_name = "_test_action_edit"
        ACTIONS_REGISTRY[test_name] = {
            "description": "Old", "required": [], "optional": {},
            "aliases": ["test_edit"], "param_aliases": {},
        }
        result = _exec_registry_edit({
            "action_name": test_name,
            "action_description": "New description",
        })
        assert "description" in result.get("changes", [])
        assert ACTIONS_REGISTRY[test_name]["description"] == "New description"
        ACTIONS_REGISTRY.pop(test_name, None)

    def test_registry_edit_nonexistent(self) -> None:
        """Edit non-existent action → error."""
        from app.system_executor import _exec_registry_edit

        result = _exec_registry_edit({"action_name": "no_such_action"})
        assert "error" in result


# ── File read ────────────────────────────────────────────────────


class TestFileRead:
    """_exec_file_read handler."""

    def test_file_read_existing(self, tmp_path, monkeypatch) -> None:
        """Read an existing file → content returned."""
        from app.system_executor import _exec_file_read

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world\nline2\n")
        # Allow access to tmp_path
        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        result = _exec_file_read({"file_path": str(test_file)})
        assert "content" in result
        assert "hello world" in result["content"]
        assert result["lines"] == 3

    def test_file_read_nonexistent(self, tmp_path, monkeypatch) -> None:
        """Read non-existent file → error."""
        from app.system_executor import _exec_file_read

        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        result = _exec_file_read({"file_path": str(tmp_path / "nope.txt")})
        assert "error" in result

    def test_file_read_no_path(self) -> None:
        """Read with empty file_path → error."""
        from app.system_executor import _exec_file_read

        result = _exec_file_read({})
        assert "error" in result


# ── File write ───────────────────────────────────────────────────


class TestFileWrite:
    """_exec_file_write handler."""

    def test_file_write_new(self, tmp_path, monkeypatch) -> None:
        """Write a new file → file created."""
        from app.system_executor import _exec_file_write

        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "read_only_paths",
            [],
        )
        target = tmp_path / "output.txt"
        result = _exec_file_write({"file_path": str(target), "content": "written"})
        assert result.get("written") is True
        assert target.read_text() == "written"

    def test_file_write_append(self, tmp_path, monkeypatch) -> None:
        """Append to existing file."""
        from app.system_executor import _exec_file_write

        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "read_only_paths",
            [],
        )
        target = tmp_path / "append.txt"
        target.write_text("first")
        result = _exec_file_write({"file_path": str(target), "content": "second", "mode": "append"})
        assert result.get("written") is True
        assert target.read_text() == "firstsecond"


# ── execute_system_action (async entry point) ───────────────────


class TestExecuteSystemAction:
    """Async dispatch function."""

    @pytest.mark.asyncio
    async def test_execute_known_action(self) -> None:
        """Known system action dispatches correctly."""
        from app.system_executor import execute_system_action

        result = await execute_system_action("system_status", {})
        assert result["status"] == "completed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self) -> None:
        """Unknown action → error in result."""
        from app.system_executor import execute_system_action

        result = await execute_system_action("nonexistent_action", {})
        assert "error" in result


# ── File path validation ─────────────────────────────────────────


class TestFilePathValidation:
    """_validate_file_path and _is_read_only."""

    def test_validate_allowed_path(self, tmp_path, monkeypatch) -> None:
        """Path within allowed_paths → resolves OK."""
        from app.system_executor import _validate_file_path

        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "allowed_paths",
            [str(tmp_path)],
        )
        test_file = tmp_path / "ok.py"
        test_file.touch()
        resolved = _validate_file_path(str(test_file))
        assert resolved == str(test_file.resolve())

    def test_validate_disallowed_path(self) -> None:
        """Path outside allowed_paths → PermissionError."""
        from app.system_executor import _validate_file_path

        with pytest.raises(PermissionError):
            _validate_file_path("/etc/passwd")

    def test_is_read_only(self, tmp_path, monkeypatch) -> None:
        """Path in read_only_paths → True."""
        from app.system_executor import _is_read_only

        ro_dir = str(tmp_path / "readonly")
        monkeypatch.setattr(
            settings_manager.settings.file_access,
            "read_only_paths",
            [ro_dir],
        )
        assert _is_read_only(ro_dir + "/file.py") is True
        assert _is_read_only(str(tmp_path / "other.py")) is False


# ── Executor mapping ─────────────────────────────────────────────


class TestExecutorMapping:
    """SYSTEM_EXECUTORS dict is complete."""

    def test_all_system_actions_have_executor(self) -> None:
        """Every system action in SYSTEM_EXECUTORS should be callable."""
        for name, executor in SYSTEM_EXECUTORS.items():
            assert callable(executor), f"Executor for '{name}' is not callable"

    def test_executors_count(self) -> None:
        """At least 8 system executors registered."""
        assert len(SYSTEM_EXECUTORS) >= 8
