"""Minimal valid PDF invoice writer (no external dependencies)."""

from __future__ import annotations

from pathlib import Path


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_invoice_pdf_bytes(*, to: str, amount: str | float, currency: str) -> bytes:
    """Return bytes of a minimal PDF 1.4 document with invoice text."""
    lines = [
        "FAKTURA",
        f"Odbiorca: {to}",
        f"Kwota: {amount} {currency}",
    ]
    y = 750
    stream_parts = ["BT"]
    for line in lines:
        stream_parts.append(f"/F1 12 Tf 72 {y} Td ({_pdf_escape(line)}) Tj")
        y -= 16
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")
    stream_len = len(stream)

    header = b"%PDF-1.4\n"
    parts: list[bytes] = [header]
    offsets: list[int] = []

    def add(obj: bytes) -> None:
        offsets.append(sum(len(p) for p in parts))
        parts.append(obj)

    add(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    add(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    add(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    add(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    body = b"".join(parts)
    xref_start = len(body)
    xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode())
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode()
        + b"\n%%EOF\n"
    )
    return body + b"".join(xref) + trailer


def write_invoice_pdf(
    path: Path | str,
    *,
    to: str,
    amount: str | float,
    currency: str = "PLN",
) -> Path:
    """Write a minimal valid PDF invoice to *path* (creates parent dirs)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build_invoice_pdf_bytes(to=to, amount=amount, currency=currency))
    return out
