#!/bin/bash
# Metrun profiling script for nlp2dsl project

echo "=== Setting up metrun profiling for nlp2dsl ==="

# Create project directory for metrun reports
mkdir -p /home/tom/github/wronai/nlp2dsl/metrun-reports

# Check if metrun is available
if ! command -v metrun &> /dev/null; then
    echo "Error: metrun is not installed or not in PATH"
    echo "Please install metrun first from: https://github.com/semcod/metrun"
    exit 1
fi

# Profile the main services
echo "Profiling NLP Service..."
cd /home/tom/github/wronai/nlp2dsl/nlp-service
metrun profile app/main.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/nlp-service-profile.txt

echo "Profiling Backend Service..."
cd /home/tom/github/wronai/nlp2dsl/backend
metrun profile app/main.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/backend-profile.txt

echo "Profiling Worker..."
cd /home/tom/github/wronai/nlp2dsl/worker
metrun profile worker.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/worker-profile.txt

# Profile an example
echo "Profiling example conversation flow..."
cd /home/tom/github/wronai/nlp2dsl/examples/05-conversation-flow
metrun profile main.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/example-conversation-profile.txt

# Generate flame graphs
echo "Generating flame graphs..."
cd /home/tom/github/wronai/nlp2dsl/nlp-service
metrun flame app/main.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/nlp-service-flame.svg

cd /home/tom/github/wronai/nlp2dsl/backend
metrun flame app/main.py --output /home/tom/github/wronai/nlp2dsl/metrun-reports/backend-flame.svg

# Run CLI flows analysis
echo "Running CLI flows analysis..."
cd /home/tom/github/wronai/nlp2dsl
metrun section --name "nlp2dsl-analysis" --output /home/tom/github/wronai/nlp2dsl/metrun-reports/cli-flows.txt

echo "=== Metrun profiling complete ==="
echo "Reports available in: /home/tom/github/wronai/nlp2dsl/metrun-reports/"
