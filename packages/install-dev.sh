#!/usr/bin/env bash
# Install integration packages in dependency order (editable).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export LANG="${LANG:-C.UTF-8}"
export LC_CTYPE="${LC_CTYPE:-$LANG}"

install_one() {
  echo "==> pip install -e $1"
  "$PY" -m pip install -e "$1" --upgrade
}

# env2llm is installed by scripts/install-local-deps.sh (sibling repo semcod/env2llm).

install_one "$ROOT/pact-ir"
install_one "$ROOT/dsl-contracts"
install_one "$ROOT/workflow-export"
install_one "$ROOT/nlp2dsl-stack"
install_one "$ROOT/testql-conversations"
install_one "$ROOT/nlp2dsl-artifacts"
install_one "$ROOT/dsl-validate"
install_one "$ROOT/nlp2cmd-intent"
install_one "$ROOT/nlp2cmd-planner"
install_one "$ROOT/nlp2cmd-propact"
install_one "$ROOT/nlp2dsl-show"

# Optional sibling publish-layer packages (markpact, pactown)
MONO_ROOT="$(cd "$ROOT/.." && pwd)"
for extra in "$MONO_ROOT/../markpact" "$MONO_ROOT/../pactown"; do
  if [[ -f "$extra/pyproject.toml" ]]; then
    install_one "$extra"
  fi
done

echo "Done."
echo "  nlp2dsl show 'znajdz pliki *.py'        # SDK: query structure (IntentIR)"
echo "  nlp2dsl-show show 'znajdz pliki *.py'  # package CLI (same)"
echo "  NLP2CMD_INTEGRATION=1 nlp2cmd plan 'znajdz pliki *.py' --explain"
