#!/usr/bin/env bash
# Ensure nlp2dsl SDK deps (pydantic, etc.) are importable in the active Python.
# Usage: PY="$(ensure_nlp2dsl_sdk /path/to/nlp2dsl/repo)" && "$PY" ...

ensure_nlp2dsl_sdk() {
  local root="$1"
  local py="${PYTHON:-python3}"

  if [[ -x "$root/.venv/bin/python3" ]]; then
    py="$root/.venv/bin/python3"
  elif [[ -x "$root/venv/bin/python3" ]]; then
    py="$root/venv/bin/python3"
  fi

  if ! "$py" -c "import env2llm, nlp2dsl_sdk" 2>/dev/null; then
    echo "==> Brak env2llm/nlp2dsl — instaluję lokalne zależności w: $py" >&2
    PYTHON="$py" bash "$root/scripts/install-local-deps.sh"
    "$py" -m pip install -e "$root" -q
  fi

  echo "$py"
}
