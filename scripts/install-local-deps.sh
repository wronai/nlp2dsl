#!/usr/bin/env bash
# Install editable local dependencies before `pip install -e .` (pip ignores [tool.uv.sources]).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export LANG="${LANG:-C.UTF-8}"
export LC_CTYPE="${LC_CTYPE:-$LANG}"

install_one() {
  local label="$1"
  local dir="$2"
  if [[ ! -f "$dir/pyproject.toml" ]]; then
    echo "ERROR: missing pyproject.toml for $label at $dir" >&2
    exit 1
  fi
  echo "==> pip install -e $dir  ($label)"
  "$PY" -m pip install -e "$dir" --upgrade
}

ENV2LLM_DIR="${ENV2LLM_DIR:-$ROOT/../../semcod/env2llm}"
if [[ -f "$ENV2LLM_DIR/pyproject.toml" ]]; then
  install_one env2llm "$ENV2LLM_DIR"
else
  echo "ERROR: env2llm not found at $ENV2LLM_DIR" >&2
  echo "  Clone semcod/env2llm or set ENV2LLM_DIR=/path/to/env2llm" >&2
  exit 1
fi

PYTHON="$PY" "$ROOT/packages/install-dev.sh"
