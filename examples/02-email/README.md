# Przykład: Wysyłanie E-maila

Podstawowy przykład pokazujący, jak wysłać e-mail za pomocą platformy NLP2DSL.

## Sposoby użycia

### 1. One-shot API

```bash
# Prosty e-mail
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyślij email do team@firma.pl z tematem Status projektu"}'

# E-mail z treścią
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Napisz email do manager@firma.pl: Projekt zakończony sukcesem"}'
```

### 2. Konwersacyjny flow

```bash
# Rozpocznij
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać email"}'

# Uzupełnij dane
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "Do: team@firma.pl, Temat: Spotkanie jutro"}'

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
    "name": "email_notification",
    "steps": [
      {"action": "send_email", "config": {"to": "team@firma.pl", "subject": "Status projektu", "body": "Projekt w 90% ukończony"}}
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

System wyśle e-mail na podany adres z określonym tematem i treścią.

## Warianty

- "Wyślij powiadomienie na admin@firma.pl" - alias "powiadomienie"
- "Maila do klient@firma.pl z ofertą" - alias "maila"
- "Napisz do zespołu o spotkaniu" - alias "napisz"
