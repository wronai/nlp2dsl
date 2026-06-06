from __future__ import annotations

from app.routers.chat import _is_explicit_execute_request


def test_go_is_not_matched_inside_polish_words() -> None:
    assert not _is_explicit_execute_request(
        {
            "text": (
                "Treść wiadomości: W załączeniu podsumowanie tygodnia. "
                "Wszystkie zadania zamknięte zgodnie z planem."
            )
        }
    )


def test_go_matches_as_standalone_execute_keyword() -> None:
    assert _is_explicit_execute_request({"text": "go"})
    assert _is_explicit_execute_request({"text": "OK, uruchom"})
