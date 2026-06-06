"""DOQL value formatting helpers for SystemMapIR render."""

from __future__ import annotations

from typing import Any


def esc_str(value: str) -> str:
    return value.replace('"', '\\"')


def esc_str_full(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def bool_lit(value: bool) -> str:
    return "true" if value else "false"


def join_csv(items: list[str]) -> str:
    return ",".join(items)


def data_value_line(key: str, val: Any) -> str:
    if isinstance(val, str):
        return f'  {key}: "{esc_str_full(val)}";'
    if isinstance(val, bool):
        return f"  {key}: {bool_lit(val)};"
    return f"  {key}: {val};"


def history_value_line(key: str, val: Any) -> str:
    if isinstance(val, list):
        return f'  {key}: "{",".join(str(v) for v in val)}";'
    if isinstance(val, str):
        return f'  {key}: "{val}";'
    return f"  {key}: {val};"


def process_field_line(key: str, val: Any) -> str:
    if isinstance(val, bool):
        return f"  {key}: {bool_lit(val)};"
    if isinstance(val, float):
        return f"  {key}: {val};"
    return f'  {key}: "{val}";'
