#!/usr/bin/env bash
# E2E test runner for NLP2DSL
#
# Usage:
#   ./tests/run.sh                  # run all tests
#   ./tests/run.sh nlp              # only nlp-service tests
#   ./tests/run.sh backend          # only backend tests
#   ./tests/run.sh ws               # only WebSocket tests
#   ./tests/run.sh ui               # only Playwright UI tests
#   ./tests/run.sh -k "health"      # pass-through pytest flags
#
# Environment:
#   NLP_URL=http://localhost:8002   (default)
#   BACKEND_URL=http://localhost:8010 (default)
#   NLP_WS_URL=ws://localhost:8002  (default)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Install deps if missing ────────────────────────────────────
if ! python3 -c "import pytest" &>/dev/null; then
    echo "[setup] Installing test dependencies..."
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
fi

if ! playwright --version &>/dev/null 2>&1; then
    echo "[setup] Installing Playwright browsers..."
    playwright install chromium
fi

# ── Resolve test target ────────────────────────────────────────
TARGET="${1:-all}"
shift 2>/dev/null || true

case "$TARGET" in
    nlp)     TEST_PATH="$SCRIPT_DIR/e2e/test_nlp_service.py" ;;
    backend) TEST_PATH="$SCRIPT_DIR/e2e/test_backend.py" ;;
    ws)      TEST_PATH="$SCRIPT_DIR/e2e/test_websocket.py" ;;
    ui)      TEST_PATH="$SCRIPT_DIR/e2e/test_chat_ui.py" ;;
    all)     TEST_PATH="$SCRIPT_DIR/e2e/" ;;
    *)
        # Treat unknown first arg as extra pytest flag
        TEST_PATH="$SCRIPT_DIR/e2e/"
        set -- "$TARGET" "$@"
        ;;
esac

# ── Health pre-check ───────────────────────────────────────────
NLP_URL="${NLP_URL:-http://localhost:8002}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8010}"

echo ""
echo "=== NLP2DSL E2E Tests ==="
echo "nlp-service : $NLP_URL"
echo "backend     : $BACKEND_URL"
echo ""

nlp_ok=0
backend_ok=0

if curl -sf "$NLP_URL/health" >/dev/null 2>&1; then
    echo "[✓] nlp-service reachable"
    nlp_ok=1
else
    echo "[✗] nlp-service NOT reachable at $NLP_URL — NLP tests will fail"
fi

if curl -sf "$BACKEND_URL/health" >/dev/null 2>&1; then
    echo "[✓] backend reachable"
    backend_ok=1
else
    echo "[✗] backend NOT reachable at $BACKEND_URL — backend tests will fail"
fi

echo ""

# ── Run pytest ─────────────────────────────────────────────────
cd "$ROOT_DIR"
python3 -m pytest \
    "$TEST_PATH" \
    --asyncio-mode=auto \
    -v \
    --tb=short \
    "$@"
