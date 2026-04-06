#!/bin/bash

set -e

echo "=== Przykład: Zaplanowane Raporty ==="
echo

# Sprawdź backend
if ! curl -s http://localhost:8010/docs > /dev/null; then
    echo "❌ Backend nie działa. Uruchom: docker compose up -d"
    exit 1
fi

echo "1️⃣  Tworzenie codziennego raportu sprzedaży..."
DAILY_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/run \
    -H "Content-Type: application/json" \
    -d '{
        "name": "daily_sales_report",
        "trigger": "daily",
        "schedule": "09:00",
        "steps": [
            {"action": "generate_report", "config": {"report_type": "sales", "format": "pdf"}},
            {"action": "send_email", "config": {"to": "team@firma.pl", "subject": "Dzienny raport sprzedaży"}}
        ]
    }')

echo "$DAILY_RESPONSE" | python3 -m json.tool
echo

echo "2️⃣  Tworzenie tygodniowego raportu HR..."
WEEKLY_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/run \
    -H "Content-Type: application/json" \
    -d '{
        "name": "weekly_hr_report",
        "trigger": "weekly",
        "schedule": "monday 08:00",
        "steps": [
            {"action": "generate_report", "config": {"report_type": "hr", "format": "xlsx"}},
            {"action": "send_email", "config": {"to": "hr@firma.pl", "subject": "Tygodniowy raport HR"}}
        ]
    }')

echo "$WEEKLY_RESPONSE" | python3 -m json.tool
echo

echo "3️⃣  Generowanie z tekstu z triggerem..."
TEXT_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/from-text \
    -H "Content-Type: application/json" \
    -d '{"text": "Codziennie o 9:00 generuj raport sprzedaży i wysyłaj do team@firma.pl"}')

echo "$TEXT_RESPONSE" | python3 -m json.tool
echo

echo "✅ Przykład zakończony!"
