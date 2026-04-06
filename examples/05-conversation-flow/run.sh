#!/bin/bash

set -e

echo "=== Przykład: Konwersacyjny Flow ==="
echo

# Sprawdź backend
if ! curl -s http://localhost:8010/docs > /dev/null; then
    echo "❌ Backend nie działa. Uruchom: docker compose up -d"
    exit 1
fi

echo "1️⃣  Rozpoczynanie rozmowy..."
START_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/chat/start \
    -H "Content-Type: application/json" \
    -d '{"text": "Chcę wysłać fakturę"}')

echo "$START_RESPONSE" | python3 -m json.tool

# Wyodrębnij conversation_id
CONVERSATION_ID=$(echo "$START_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")
echo "📝 Conversation ID: $CONVERSATION_ID"
echo

echo "2️⃣  Uzupełnianie danych..."
MESSAGE_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/chat/message \
    -H "Content-Type: application/json" \
    -d "{\"conversation_id\": \"$CONVERSATION_ID\", \"text\": \"1500 PLN na klient@firma.pl\"}")

echo "$MESSAGE_RESPONSE" | python3 -m json.tool
echo

echo "3️⃣  Wykonywanie workflow..."
EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:8010/workflow/chat/message \
    -H "Content-Type: application/json" \
    -d "{\"conversation_id\": \"$CONVERSATION_ID\", \"text\": \"uruchom\"}")

echo "$EXECUTE_RESPONSE" | python3 -m json.tool
echo

echo "✅ Konwersacja zakończona!"

# Pokaż historię
echo
echo "📚 Historia konwersacji:"
echo "1. Użytkownik: Chcę wysłać fakturę"
echo "   System: Podaj: kwotę, adres e-mail odbiorcy"
echo "2. Użytkownik: 1500 PLN na klient@firma.pl"
echo "   System: Workflow gotowy. Wyślij 'uruchom' aby wykonać."
echo "3. Użytkownik: uruchom"
echo "   System: Workflow wykonany"
