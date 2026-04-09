#!/bin/bash
# Pfix-compatible test wrapper
# Runs tests and ensures exit code is properly interpreted

cd /home/tom/github/wronai/nlp2dsl || exit 1

# Run tests - only exit code matters
if python3 -m pytest tests/ -q --tb=no >/dev/null 2>&1; then
    echo "SUCCESS: All tests passed"
    exit 0
else
    echo "FAILURE: Tests failed"
    exit 1
fi

#find /home/tom/github/semcod -type f -exec sed -i 's/gpt-4o-mini/gpt-5.4-mini/g' {} \;