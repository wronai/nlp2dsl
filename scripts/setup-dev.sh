#!/usr/bin/env bash
# Full dev setup: nlp2dsl packages + SDK + nlp2cmd integration.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
NLP2CMD_DIR="${NLP2CMD_DIR:-$ROOT/../nlp2cmd}"

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export LANG="${LANG:-C.UTF-8}"
export LC_CTYPE="${LC_CTYPE:-$LANG}"

echo "==> nlp2dsl packages (pact-ir, intent, planner, propact, show)"
"$ROOT/packages/install-dev.sh"

echo "==> nlp2dsl SDK"
"$PY" -m pip install -e "$ROOT"

if [[ -d "$NLP2CMD_DIR" ]]; then
  echo "==> nlp2cmd + integration ($NLP2CMD_DIR)"
  "$PY" -m pip install -e "$NLP2CMD_DIR[integration]"
  # pip install nlp2cmd[integration] can overwrite editable packages with wheels —
  # restore editable sources from packages/
  echo "==> Re-pin editable packages (post nlp2cmd[integration])"
  "$ROOT/packages/install-dev.sh"
else
  echo "WARN: nlp2cmd not found at $NLP2CMD_DIR — skip (set NLP2CMD_DIR=...)" >&2
fi

echo ""
echo "Done. Suggested env:"
echo "  export NLP2CMD_INTEGRATION=1"
echo "  (UTF-8 locale: automatycznie przez nlp2dsl_sdk — patrz docs/encoding.md)"
echo ""
echo "Try:"
echo "  nlp2dsl show 'znajdz pliki *.py w src'"
echo "  nlp2cmd plan 'znajdz pliki *.py w src' --explain"
echo "  nlp2cmd plan 'znajdz pliki *.py w src' --execute"
echo "  NLP2CMD_SHOW_STRUCTURE=1 nlp2cmd -q 'znajdz pliki *.py w src' --explain"
echo ""
echo "Workflow REST (optional, backend must be running):"
echo "  export NLP2CMD_NLP2DSL_WORKFLOW=1 NLP2DSL_BACKEND_URL=http://127.0.0.1:8010"
echo "  nlp2cmd plan 'Wyslij fakture na 1500 PLN do a@b.pl' --json"
