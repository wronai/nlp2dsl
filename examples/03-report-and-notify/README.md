# Przykład: Raport i Powiadomienia

Zaawansowany przykład pokazujący, jak zautomatyzować generowanie raportu i wysyłanie powiadomień do wielu kanałów.

## Scenariusz

Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl oraz powiadomienie na Slack #sales

## Sposoby użycia

### 1. One-shot API (composite intent)

```bash
# Automatyczne rozpoznanie wielu akcji
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl oraz powiadom na Slack #sales"}'

# Generuj i wykonaj od razu
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Generuj raport sprzedaży i powiadom team", "execute": true}'
```

### 2. Konwersacyjny flow

```bash
# Rozpocznij rozmowę
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę zautomatyzować raporty sprzedaży"}'

# System dopyta o szczegóły...
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "Raport sprzedaży w PDF, email do manager, powiadomienie na #sales"}'

# Uruchom
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "uruchom"}'
```

### 3. Bezpośrednie wywołanie DSL

```bash
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weekly_sales_report",
    "trigger": "weekly",
    "steps": [
      {"action": "generate_report", "config": {"report_type": "sales", "format": "pdf"}},
      {"action": "send_email", "config": {"to": "manager@firma.pl", "subject": "Tygodniowy raport sprzedaży", "body": "W załączniku znajdziesz raport sprzedaży za ostatni tydzień."}},
      {"action": "notify_slack", "config": {"channel": "#sales", "message": "📊 Nowy raport sprzedaży jest dostępny!"}}
    ]
  }'
```

## Uruchomienie przykładu

```bash
./run.sh
# lub
python3 main.py
```

## Oczekiwany wynik

1. Wygenerowany raport PDF sprzedaży
2. E-mail wysłany do manager@firma.pl z załącznikiem
3. Powiadomienie na kanale #sales Slack

## Warianty

- "Raport HR i powiadomienie na #hr" - zmienia typ raportu i kanał
- "Miesięczny raport finansów do CFO" - zmienia częstotliwość i odbiorcę
- "Generuj raport marketingowy i wyślij do teamu" - inny typ raportu
