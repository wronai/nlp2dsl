from app.execution.delegate import (
    delegate_payload,
    execution_backend_for_intent,
    is_delegated_to_mullm,
)

__all__ = [
    "SYSTEM_EXECUTORS",
    "delegate_payload",
    "execute_system_action",
    "execution_backend_for_intent",
    "is_delegated_to_mullm",
]


def __getattr__(name: str):
    if name in {"SYSTEM_EXECUTORS", "execute_system_action"}:
        from app.execution import system

        return getattr(system, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
