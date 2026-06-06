"""Shared validation helpers."""

from __future__ import annotations

import re
from typing import Any


def is_empty(val: Any) -> bool:
    return val is None or (isinstance(val, str) and not val.strip())


def parse_amount(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def pdf_structure_issues(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF"):
        return ["attachment_path: wymagany prawidłowy PDF (%PDF), a plik nim nie jest"]
    if b"%%EOF" not in data[-2048:]:
        return ["attachment_path: plik PDF nie ma poprawnego zakończenia (%%EOF)"]
    return []


def pdf_amount_mismatch(data: bytes, expected_amount: float) -> str | None:
    text = data.decode("latin-1", errors="ignore")
    match = re.search(r"Kwota:\s*([\d.]+)", text)
    if not match:
        return None
    file_amount = float(match.group(1))
    if abs(file_amount - expected_amount) > 0.01:
        return f"attachment_path: kwota w pliku ({file_amount}) ≠ w request ({expected_amount})"
    return None
