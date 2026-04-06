# Przykład: Zaplanowane Raporty

Zaawansowany przykład pokazujący, jak skonfigurować automatyczne generowanie raportów według harmonogramu.

## Scenariusze

1. **Codzienny raport sprzedaży** - każdy dzień o 9:00
2. **Tygodniowy raport HR** - każdy poniedziałek o 8:00
3. **Miesięczny raport finansowy** - pierwszego dnia miesiąca o 7:00

## Sposoby użycia

### 1. One-shot API z triggerem

```bash
# Raport codzienny
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Codziennie o 9:00 generuj raport sprzedaży i wysyłaj do team@firma.pl"}'

# Raport tygodniowy
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Co poniedziałek generuj raport HR i wyślij do hr@firma.pl"}'

# Raport miesięczny
curl -X POST http://localhost:8010/workflow/from-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Pierwszego każdego miesiąca raport finansów do CFO"}'
```

### 2. Bezpośrednie wywołanie DSL z triggerem

```bash
# Codzienny raport
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_sales_report",
    "trigger": "daily",
    "schedule": "09:00",
    "steps": [
      {"action": "generate_report", "config": {"report_type": "sales", "format": "pdf"}},
      {"action": "send_email", "config": {"to": "team@firma.pl", "subject": "Dzienny raport sprzedaży"}}
    ]
  }'

# Tygodniowy raport
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weekly_hr_report",
    "trigger": "weekly",
    "schedule": "monday 08:00",
    "steps": [
      {"action": "generate_report", "config": {"report_type": "hr", "format": "xlsx"}},
      {"action": "send_email", "config": {"to": "hr@firma.pl", "subject": "Tygodniowy raport HR"}}
    ]
  }'

# Miesięczny raport
curl -X POST http://localhost:8010/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "monthly_finance_report",
    "trigger": "monthly",
    "schedule": "1st 07:00",
    "steps": [
      {"action": "generate_report", "config": {"report_type": "finance", "format": "pdf"}},
      {"action": "send_email", "config": {"to": "cfo@firma.pl", "subject": "Miesięczny raport finansowy"}}
    ]
  }'
```

### 3. Konwersacyjny flow

```bash
# Rozpocznij
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę zaplanować automatyczne raporty"}'

# System dopyta o szczegóły...
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "Codziennie o 9 raport sprzedaży do teamu"}'

# Uruchom
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "uruchom"}'
```

## Uruchomienie przykładu

```bash
./run.sh
# lub
python3 main.py
```

## Opcje harmonogramu

- `daily` - codziennie (z opcjonalną godziną)
- `weekly` - co tydzień (z dniem i godziną)
- `monthly` - co miesiąc (z dniem miesiąca i godziną)
- `cron` - wyrażenie cron dla zaawansowanych

## Warianty

- "Każdy dzień roboczy o 17" - tylko dni robocze
- "Co 2 godziny raport systemowy" - interwał godzinowy
- "W każdą niedzielę podsumowanie tygodnia" - konkretny dzień tygodnia
