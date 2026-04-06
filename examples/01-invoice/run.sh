#!/bin/bash

set -e

echo "=== Przykład: Wysyłanie Faktury ==="
echo

# Sprawdź, czy backend działa
if ! curl -s http://localhost:8010/docs > /dev/null; then
    echo "❌ Backend nie działa. Uruchom: docker compose up -d"
    exit 1
fi

echo "1️⃣  Generowanie DSL z tekstu..."
RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/from-text \
    -H "Content-Type: application/json" \
    -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl"}')

echo "$RESPONSE" | python3 -m json.tool
echo

echo "2️⃣  Wykonywanie workflow..."
EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/run \
    -H "Content-Type: application/json" \
    -d '{
        "name": "invoice_example",
        "steps": [
            {"action": "send_invoice", "config": {"amount": 1500, "to": "klient@firma.pl", "currency": "PLN"}}
        ]
    }')

echo "$EXECUTE_RESPONSE" | python3 -m json.tool
echo

echo "✅ Przykład zakończony!"
