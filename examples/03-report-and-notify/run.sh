#!/bin/bash

set -e

echo "=== Przykład: Raport i Powiadomienia ==="
echo

# Sprawdź backend
if ! curl -s http://localhost:8010/docs > /dev/null; then
    echo "❌ Backend nie działa. Uruchom: docker compose up -d"
    exit 1
fi

echo "1️⃣  Generowanie DSL z tekstu (composite intent)..."
RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/from-text \
    -H "Content-Type: application/json" \
    -d '{"text": "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl oraz powiadom na Slack #sales"}')

echo "$RESPONSE" | python3 -m json.tool
echo

echo "2️⃣  Wykonywanie workflow z wieloma krokami..."
EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/run \
    -H "Content-Type: application/json" \
    -d '{
        "name": "weekly_sales_report",
        "trigger": "weekly",
        "steps": [
            {"action": "generate_report", "config": {"report_type": "sales", "format": "pdf"}},
            {"action": "send_email", "config": {"to": "manager@firma.pl", "subject": "Tygodniowy raport sprzedaży", "body": "W załączniku znajdziesz raport sprzedaży za ostatni tydzień."}},
            {"action": "notify_slack", "config": {"channel": "#sales", "message": "📊 Nowy raport sprzedaży jest dostępny!"}}
        ]
    }')

echo "$EXECUTE_RESPONSE" | python3 -m json.tool
echo

echo "✅ Przykład zakończony!"
