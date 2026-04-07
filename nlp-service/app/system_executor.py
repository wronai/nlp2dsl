"""
System Executor — obsługa akcji systemowych.

Akcje systemowe (settings, files, registry) są wykonywane
LOKALNIE w nlp-service, nie delegowane do workera.

Wzorzec:
  biznesowe akcje → worker (Docker)
  systemowe akcje → system_executor (lokalnie)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .registry import ACTIONS_REGISTRY, BUSINESS_ACTIONS, SYSTEM_ACTIONS
from .settings import settings_manager

log = logging.getLogger("system.executor")


# ── File safety ───────────────────────────────────────────────

def _validate_file_path(file_path: str) -> str:
    """Validate and resolve file path against allowed paths."""
    fa = settings_manager.settings.file_access
    resolved = str(Path(file_path).resolve())

    # Check allowed paths
    allowed = any(resolved.startswith(p) for p in fa.allowed_paths)
    if not allowed:
        raise PermissionError(
            f"Dostęp do '{file_path}' zabroniony. "
            f"Dozwolone ścieżki: {fa.allowed_paths}"
        )

    # Check extension
    ext = Path(file_path).suffix.lower()
    if ext and ext not in fa.allowed_extensions:
        raise PermissionError(
            f"Rozszerzenie '{ext}' niedozwolone. "
            f"Dozwolone: {fa.allowed_extensions}"
        )

    return resolved


def _is_read_only(file_path: str) -> bool:
    """Check if path is in read-only zone."""
    fa = settings_manager.settings.file_access
    resolved = str(Path(file_path).resolve())
    return any(resolved.startswith(p) for p in fa.read_only_paths)


# ── Executors ─────────────────────────────────────────────────


async def execute_system_action(action: str, config: dict) -> dict:
    """Route and execute system action."""
    executor = SYSTEM_EXECUTORS.get(action)
    if not executor:
        return {"error": f"Unknown system action: {action}"}

    try:
        result = executor(config)
        log.info("✔ System action: %s", action)
        return {"action": action, "status": "completed", "result": result}
    except Exception as e:
        log.exception("✗ System action failed: %s", action)
        return {"action": action, "status": "failed", "error": str(e)}


# ── Settings ──────────────────────────────────────────────────


def _exec_settings_get(config: dict) -> dict:
    section = config.get("section", "all")
    if section == "all":
        return {
            "settings": settings_manager.get_all(),
            "schema": settings_manager.describe(),
        }
    return {
        "section": section,
        "settings": settings_manager.get_section(section),
    }


def _exec_settings_set(config: dict) -> dict:
    path = config.get("setting_path")
    value = config.get("setting_value")
    if not path:
        return {"error": "Brak setting_path"}
    if value is None:
        return {"error": "Brak setting_value"}

    return settings_manager.set(path, value)


def _exec_settings_reset(config: dict) -> dict:
    section = config.get("section")
    if section and section != "all":
        return settings_manager.reset(section)
    return settings_manager.reset()


# ── Files ─────────────────────────────────────────────────────


def _exec_file_read(config: dict) -> dict:
    file_path = config.get("file_path", "")
    if not file_path:
        return {"error": "Brak file_path"}

    resolved = _validate_file_path(file_path)

    if not Path(resolved).exists():
        return {"error": f"Plik nie istnieje: {file_path}"}

    if not Path(resolved).is_file():
        return {"error": f"Ścieżka nie jest plikiem: {file_path}"}

    # Size check
    size_kb = Path(resolved).stat().st_size / 1024
    max_kb = settings_manager.settings.file_access.max_file_size_kb
    if size_kb > max_kb:
        return {"error": f"Plik za duży: {size_kb:.0f}KB (max {max_kb}KB)"}

    content = Path(resolved).read_text(errors="replace")

    # Line range
    line_start = config.get("line_start", 0)
    line_end = config.get("line_end", 0)
    if line_start or line_end:
        lines = content.split("\n")
        start = max(0, (line_start or 1) - 1)
        end = line_end or len(lines)
        content = "\n".join(lines[start:end])

    return {
        "file_path": file_path,
        "size_kb": round(size_kb, 1),
        "lines": content.count("\n") + 1,
        "content": content,
    }


def _exec_file_write(config: dict) -> dict:
    file_path = config.get("file_path", "")
    content = config.get("content", "")
    mode = config.get("mode", "write")

    if not file_path:
        return {"error": "Brak file_path"}

    resolved = _validate_file_path(file_path)

    if _is_read_only(resolved):
        return {"error": f"Plik jest w strefie read-only: {file_path}"}

    p = Path(resolved)
    p.parent.mkdir(parents=True, exist_ok=True)

    if mode == "append":
        with open(p, "a") as f:
            f.write(content)
    else:
        p.write_text(content)

    return {
        "file_path": file_path,
        "mode": mode,
        "size_kb": round(p.stat().st_size / 1024, 1),
        "written": True,
    }


def _exec_file_list(config: dict) -> dict:
    directory = config.get("directory", ".")
    pattern = config.get("pattern", "*")

    # Resolve relative to project root
    base_paths = settings_manager.settings.file_access.allowed_paths
    resolved = None

    for base in base_paths:
        candidate = Path(base) / directory
        if candidate.exists():
            resolved = candidate
            break

    if not resolved:
        resolved = Path(directory)
        if not resolved.exists():
            return {"error": f"Katalog nie istnieje: {directory}"}

    files = []
    for p in sorted(resolved.rglob(pattern)):
        if p.is_file() and "__pycache__" not in str(p):
            rel = str(p.relative_to(resolved))
            files.append({
                "path": rel,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "ext": p.suffix,
            })

    return {
        "directory": str(resolved),
        "pattern": pattern,
        "count": len(files),
        "files": files[:100],  # limit
    }


# ── Registry ─────────────────────────────────────────────────


def _exec_registry_list(config: dict) -> dict:
    category = config.get("category", "all")

    result = {}
    for name, meta in ACTIONS_REGISTRY.items():
        action_cat = meta.get("category", "business")
        if category != "all" and action_cat != category:
            continue
        result[name] = {
            "description": meta["description"],
            "category": action_cat,
            "required": meta.get("required", []),
            "optional": list(meta.get("optional", {}).keys()),
            "aliases": meta.get("aliases", [])[:5],  # truncate for readability
        }

    return {"count": len(result), "actions": result}


def _exec_registry_add(config: dict) -> dict:
    name = config.get("action_name", "")
    description = config.get("action_description", "")

    if not name:
        return {"error": "Brak action_name"}
    if not description:
        return {"error": "Brak action_description"}

    if name in ACTIONS_REGISTRY:
        return {"error": f"Akcja '{name}' już istnieje. Użyj system_registry_edit."}

    # Parse required fields and aliases from strings
    required = config.get("required_fields", [])
    if isinstance(required, str):
        required = [f.strip() for f in required.split(",") if f.strip()]

    aliases = config.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [a.strip() for a in aliases.split(",") if a.strip()]

    ACTIONS_REGISTRY[name] = {
        "description": description,
        "required": required,
        "optional": {},
        "aliases": aliases or [name],
        "param_aliases": {},
    }

    return {"added": name, "description": description, "required": required}


def _exec_registry_edit(config: dict) -> dict:
    name = config.get("action_name", "")
    if not name or name not in ACTIONS_REGISTRY:
        return {"error": f"Akcja '{name}' nie istnieje"}

    meta = ACTIONS_REGISTRY[name]
    changes = []

    if config.get("action_description"):
        meta["description"] = config["action_description"]
        changes.append("description")

    if config.get("required_fields") is not None:
        fields = config["required_fields"]
        if isinstance(fields, str):
            fields = [f.strip() for f in fields.split(",") if f.strip()]
        meta["required"] = fields
        changes.append("required")

    if config.get("aliases") is not None:
        new_aliases = config["aliases"]
        if isinstance(new_aliases, str):
            new_aliases = [a.strip() for a in new_aliases.split(",") if a.strip()]
        meta["aliases"] = new_aliases
        changes.append("aliases")

    return {"edited": name, "changes": changes}


# ── Status ────────────────────────────────────────────────────


def _exec_status(config: dict) -> dict:
    provider = "none"
    for env_key, prov in [
        ("OPENROUTER_API_KEY", "openrouter"),
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("OPENAI_API_KEY", "openai"),
        ("GROQ_API_KEY", "groq"),
    ]:
        if os.getenv(env_key):
            provider = prov
            break

    return {
        "version": settings_manager.settings.version,
        "llm_provider": provider,
        "llm_model": settings_manager.settings.llm.model,
        "nlp_mode": settings_manager.settings.nlp.default_mode,
        "actions_total": len(ACTIONS_REGISTRY),
        "actions_business": len(BUSINESS_ACTIONS),
        "actions_system": len(SYSTEM_ACTIONS),
        "settings_updated": settings_manager.settings.updated_at,
    }


# ── Executor mapping ─────────────────────────────────────────

SYSTEM_EXECUTORS: dict[str, callable] = {
    "system_settings_get": _exec_settings_get,
    "system_settings_set": _exec_settings_set,
    "system_settings_reset": _exec_settings_reset,
    "system_file_read": _exec_file_read,
    "system_file_write": _exec_file_write,
    "system_file_list": _exec_file_list,
    "system_registry_list": _exec_registry_list,
    "system_registry_add": _exec_registry_add,
    "system_registry_edit": _exec_registry_edit,
    "system_status": _exec_status,
}
