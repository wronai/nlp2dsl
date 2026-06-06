#!/usr/bin/env bash
# Create/use nlp2dsl/.venv and install editable monorepo packages for tests.
# Use this instead of `uv pip install` while another project's venv is active (e.g. koru).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV%/}" != "${VENV}" ]]; then
  echo "WARN: foreign VIRTUAL_ENV=$VIRTUAL_ENV — using UV_PROJECT_ENVIRONMENT=$VENV" >&2
fi

export UV_PROJECT_ENVIRONMENT="$VENV"

if [[ ! -x "$VENV/bin/python3" ]]; then
  echo "==> Creating $VENV"
  uv venv "$VENV"
fi

echo "==> Installing local deps + nlp2dsl into $VENV"
PYTHON="$VENV/bin/python3" bash "$ROOT/scripts/install-local-deps.sh"
uv pip install --python "$VENV/bin/python3" \
  -e "$ROOT[dev]" \
  -e "$ROOT/backend" \
  -e "$ROOT/nlp-service" \
  -e "$ROOT/worker"

echo ""
echo "Done. Activate:"
echo "  source $VENV/bin/activate"
echo "Or run tests without activate:"
echo "  $ROOT/run-all-tests.sh"
