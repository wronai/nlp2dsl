#!/bin/bash
# Run all test suites in the monorepo
# Usage: ./run-all-tests.sh [pytest-options]
# (Must be invoked with ./ or bash — not on PATH by default.)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIL=0

_venv_ready() {
    local candidate="$1"
    [[ -x "$candidate" || "$candidate" == "python3" ]] || return 1
    "$candidate" -c "import pytest" 2>/dev/null || return 1
    # FastAPI rejects the unrelated PyPI `multipart` package (often on system Python).
    "$candidate" -c "import multipart; assert hasattr(multipart, '__version__')" 2>/dev/null || return 1
    return 0
}

_py() {
    local venv_py="$SCRIPT_DIR/.venv/bin/python3"

    if _venv_ready "$venv_py"; then
        echo "$venv_py"
        return 0
    fi

    echo "==> Bootstrapping $SCRIPT_DIR/.venv for tests (pytest + services)..." >&2
    "$SCRIPT_DIR/scripts/bootstrap-venv.sh" >&2

    if _venv_ready "$venv_py"; then
        echo "$venv_py"
        return 0
    fi

    local candidate
    for candidate in /usr/bin/python3 python3; do
        if _venv_ready "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done

    echo "ERROR: No Python with pytest and python-multipart. Run: $SCRIPT_DIR/scripts/bootstrap-venv.sh" >&2
    exit 1
}

PYTHON="$(_py)"

if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV%/}" != "${SCRIPT_DIR}/.venv" ]]; then
    echo "INFO: Active VIRTUAL_ENV=$VIRTUAL_ENV (tests use: $PYTHON)"
    echo ""
fi

echo "Using Python: $PYTHON"
echo "==================================================="
echo "NLP2DSL - Test Suite Runner"
echo "==================================================="
echo ""

run_tests() {
    local name="$1"
    local dir="$2"
    shift 2

    echo ">> Running $name tests..."
    if cd "$dir" && "$PYTHON" -m pytest tests/ -q "$@" 2>&1; then
        echo "  OK: $name tests passed"
        return 0
    else
        echo "  FAIL: $name tests failed"
        return 1
    fi
}

# Run each test suite
run_tests "SDK" "$SCRIPT_DIR" -p no:warnings || FAIL=1
run_tests "Backend" "$SCRIPT_DIR/backend" || FAIL=1
run_tests "NLP-Service" "$SCRIPT_DIR/nlp-service" || FAIL=1
run_tests "Worker" "$SCRIPT_DIR/worker" || FAIL=1

echo ""
echo "==================================================="
if [ $FAIL -eq 0 ]; then
    echo "OK: All test suites passed!"
    exit 0
else
    echo "FAIL: Some test suites failed"
    exit 1
fi
