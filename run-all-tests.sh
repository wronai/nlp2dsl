#!/bin/bash
# Run all test suites in the monorepo
# Usage: ./run-all-tests.sh [pytest-options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIL=0

_py() {
    local candidate
    for candidate in \
        "$SCRIPT_DIR/.venv/bin/python3" \
        /usr/bin/python3 \
        python3; do
        if [[ -x "$candidate" || "$candidate" == "python3" ]] \
            && "$candidate" -c "import pytest" 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    echo python3
}

PYTHON="$(_py)"

if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV%/}" != "${SCRIPT_DIR}/.venv" ]]; then
    echo "ℹ️  Active VIRTUAL_ENV=$VIRTUAL_ENV (tests use: $PYTHON)"
    echo ""
fi

echo "Using Python: $PYTHON"
echo "═══════════════════════════════════════════════════"
echo "NLP2DSL - Test Suite Runner"
echo "═══════════════════════════════════════════════════"
echo ""

run_tests() {
    local name="$1"
    local dir="$2"
    shift 2

    echo "▶ Running $name tests..."
    if cd "$dir" && "$PYTHON" -m pytest tests/ -q "$@" 2>&1; then
        echo "  ✓ $name tests passed"
        return 0
    else
        echo "  ✗ $name tests failed"
        return 1
    fi
}

# Run each test suite
run_tests "SDK" "$SCRIPT_DIR" -p no:warnings || FAIL=1
run_tests "Backend" "$SCRIPT_DIR/backend" || FAIL=1
run_tests "NLP-Service" "$SCRIPT_DIR/nlp-service" || FAIL=1
run_tests "Worker" "$SCRIPT_DIR/worker" || FAIL=1

echo ""
echo "═══════════════════════════════════════════════════"
if [ $FAIL -eq 0 ]; then
    echo "✓ All test suites passed!"
    exit 0
else
    echo "✗ Some test suites failed"
    exit 1
fi
