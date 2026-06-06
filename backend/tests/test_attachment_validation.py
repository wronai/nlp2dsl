"""Backend attachment validation extraction and enrichment."""

from __future__ import annotations

from pathlib import Path

from app.attachment_validation import ensure_attachment_validation, validation_from_chat_result


def _write_pdf(path: Path, *, amount: int = 1500) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        + f"Kwota: {amount} PLN\n".encode("ascii")
        + b"%%EOF\n"
    )


def test_validation_from_chat_result_prefers_top_level() -> None:
    av = {"path": "x.pdf", "resolved": "/tmp/x.pdf", "status": "ok", "issues": []}

    assert validation_from_chat_result({"attachment_validation": av}) is av


def test_validation_from_chat_result_reads_execution_step_result() -> None:
    av = {"path": "worker.pdf", "resolved": "/tmp/worker.pdf", "status": "ok", "issues": []}
    result = {
        "execution": {
            "steps": [
                {"result": {"attachment_validation": av}},
            ]
        }
    }

    assert validation_from_chat_result(result) is av


def test_validation_from_chat_result_builds_from_dsl(tmp_path: Path) -> None:
    pdf = tmp_path / "invoice.pdf"
    _write_pdf(pdf)
    result = {
        "dsl": {
            "steps": [
                {
                    "action": "send_invoice",
                    "config": {
                        "amount": 1500,
                        "to": "client@example.com",
                        "attachment_path": str(pdf),
                    },
                }
            ]
        }
    }

    av = validation_from_chat_result(result)

    assert av is not None
    assert av["status"] == "ok"
    assert av["resolved"] == str(pdf)


def test_ensure_attachment_validation_marks_unused_invalid_attachment(tmp_path: Path) -> None:
    missing_pdf = tmp_path / "missing.pdf"
    result = {
        "status": "executed",
        "dsl": {
            "steps": [
                {
                    "action": "send_invoice",
                    "config": {
                        "amount": 1500,
                        "to": "client@example.com",
                        "attachment_path": str(missing_pdf),
                    },
                }
            ]
        },
        "execution": {
            "steps": [
                {"result": {"attachment_used": True}},
            ]
        },
    }

    ensure_attachment_validation(result)

    av = result["attachment_validation"]
    step_result = result["execution"]["steps"][0]["result"]
    assert av["status"] == "missing"
    assert step_result["attachment_validation"] == av
    assert step_result["attachment_used"] is False
