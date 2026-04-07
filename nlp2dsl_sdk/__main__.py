"""Module entrypoint for the reusable NLP2DSL SDK."""

from __future__ import annotations

import argparse

from .demos import list_available_demos


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an NLP2DSL SDK demo")
    parser.add_argument(
        "demo",
        nargs="?",
        default="invoice",
        help="Nazwa demo do uruchomienia (domyślnie: invoice)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Pokaż dostępne demo i zakończ",
    )
    args = parser.parse_args()

    specs = list_available_demos()
    spec_map = {spec.name: spec for spec in specs}

    if args.list:
        print("Dostępne demo:")
        for spec in specs:
            print(f"- {spec.name}: {spec.description}")
        return

    if args.demo not in spec_map:
        parser.error(f"Unknown demo '{args.demo}'. Use --list to inspect available demos.")

    spec_map[args.demo].runner()


if __name__ == "__main__":
    main()
