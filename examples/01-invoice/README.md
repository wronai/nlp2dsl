# Przykład: Wysyłanie Faktury

Podstawowy przykład pokazujący, jak wysłać fakturę za pomocą platformy NLP2DSL.

## Sposoby użycia

### 1. One-shot API (bez konwersacji)

```bash
# Generuj DSL
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl"}'

# Generuj i wykonaj od razu
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij fakturę na 1500 PLN do klient@firma.pl", "execute": true}'
```

### 2. Konwersacyjny flow

```bash
# Rozpocznij rozmowę
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać fakturę"}'

# Uzupełnij dane (conversation_id z poprzedniej odpowiedzi)
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "1500 PLN na klient@firma.pl"}'

# Uruchom workflow
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "uruchom"}'
```

### 3. Bezpośrednie wywołanie DSL

```bash
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "invoice_example",
    "steps": [
      {"action": "send_invoice", "config": {"amount": 1500, "to": "klient@firma.pl", "currency": "PLN"}}
    ]
  }'
```

## Uruchomienie przykładu

```bash
# Użyj skryptu Python
./run.sh

# Lub bezpośrednio
python3 main.py
```

## Oczekiwany wynik

System wygeneruje fakturę ID: `INV-YYYYMMDDHHMMSS` i wyśle ją na podany adres e-mail.

## Warianty

- "Wystaw rachunek na 200 EUR" - zmieni walutę
- "Faktura pro forma na 5000 PLN" - doda typ faktury (gdy obsługiwane)
- "Wyślij fakturę do wielu odbiorców" - obsługa listy e-maili (gdy obsługiwane)
