#!/usr/bin/env bash
# Run all examples/*.*/main.py from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# UTF-8: SDK ustawia to przy imporcie; poniżej dla subprocessów / starszych shelli
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export PYTHONUTF8="${PYTHONUTF8:-1}"
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-$LANG}"
export LC_CTYPE="${LC_CTYPE:-$LANG}"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PY="$ROOT/.venv/bin/python3"
elif [[ -x "$ROOT/venv/bin/python3" ]]; then
  PY="$ROOT/venv/bin/python3"
else
  PY="${PYTHON:-python3}"
fi

echo "==> Installing env2llm + packages + nlp2dsl SDK (editable)..."
PYTHON="$PY" bash "$ROOT/scripts/install-local-deps.sh"
"$PY" -m pip install -e . -q

failed=0
for dir in "$ROOT"/examples/*/; do
  name="$(basename "$dir")"
  if [[ ! -f "$dir/main.py" ]]; then
    continue
  fi
  echo ""
  echo "=== Testing examples/$name ==="
  if (cd "$dir" && "$PY" main.py); then
    echo "OK: examples/$name"
  else
    echo "FAILED: examples/$name" >&2
    failed=1
  fi
done

echo ""
echo "==> Aggregating testql from examples/*/.nlp2dsl/ ..."
"$PY" "$ROOT/scripts/aggregate-example-testql.py" || true

echo ""
echo "==> TestQL results per example (.nlp2dsl/result.*) ..."
testql_failed=0
if ! "$PY" "$ROOT/scripts/run-example-testql-results.py"; then
  testql_failed=1
  echo "WARN: some example testql results failed (see examples/*/.nlp2dsl/result.toon.yaml)" >&2
fi

if [[ "$failed" -ne 0 ]]; then
  echo ""
  echo "Some examples failed. Ensure platform is up: docker compose up -d (from repo root)" >&2
  exit 1
fi

if [[ "$testql_failed" -ne 0 ]]; then
  echo ""
  echo "Examples OK but testql result checks reported failures." >&2
  exit 1
fi

echo ""
echo "==> Contract draft validate (LLM-generated) ..."
"$PY" "$ROOT/scripts/validate-contract-draft.py" --strict

echo ""
echo "All examples passed."
