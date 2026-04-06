#!/bin/bash

set -e

echo "=== Przykład: Wysyłanie E-maila ==="
echo

# Sprawdź backend
if ! curl -s http://localhost:8010/docs > /dev/null; then
    echo "❌ Backend nie działa. Uruchom: docker compose up -d"
    exit 1
fi

echo "1️⃣  Generowanie DSL z tekstu..."
RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/from-text \
    -H "Content-Type: application/json" \
    -d '{"text": "Wyślij email do team@firma.pl z tematem Status projektu"}')

echo "$RESPONSE" | python3 -m json.tool
echo

echo "2️⃣  Wykonywanie workflow..."
EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/run \
    -H "Content-Type: application/json" \
    -d '{
        "name": "email_example",
        "steps": [
            {"action": "send_email", "config": {"to": "team@firma.pl", "subject": "Status projektu", "body": "Projekt przebiega zgodnie z planem"}}
        ]
    }')

echo "$EXECUTE_RESPONSE" | python3 -m json.tool
echo

echo "✅ Przykład zakończony!"
