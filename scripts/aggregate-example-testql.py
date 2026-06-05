#!/usr/bin/env python3
"""Merge examples/*/.nlp2dsl/commands.testql.toon.yaml → testql-scenarios/generated-examples.testql.toon.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "testql-scenarios" / "generated-examples.testql.toon.yaml"


def main() -> int:
    parts: list[str] = [
        "# SCENARIO: NLP2DSL Examples (aggregated)",
        "# TYPE: cli",
        "# GENERATED: true",
        "# PIPELINE: NLP → DSL → CMD → process",
        "",
        "CONFIG[2]{key, value}:",
        "  timeout_ms, 180000",
        "  repo_root, .",
        "",
    ]

    found = 0
    for path in sorted(ROOT.glob("examples/*/.nlp2dsl/commands.testql.toon.yaml")):
        example = path.parent.parent.name
        body = path.read_text(encoding="utf-8")
        parts.append(f"# --- {example} ---")
        for line in body.splitlines():
            if line.startswith("# SCENARIO") or line.startswith("# TYPE") or line.startswith("# GENERATED"):
                continue
            parts.append(line)
        parts.append("")
        found += 1

    if not found:
        print("No example testql files found. Run: bash examples/run-all.sh", file=sys.stderr)
        return 1

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({found} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
