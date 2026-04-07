# Przykład: Zaplanowane Raporty

Zaawansowany przykład pokazujący, jak skonfigurować automatyczne generowanie raportów według harmonogramu.

Ten katalog jest cienkim wrapperem nad `run_scheduled_report_demo()` z pakietu `nlp2dsl_sdk`.

## Scenariusze

1. **Codzienny raport sprzedaży** - każdy dzień o 9:00
2. **Tygodniowy raport HR** - każdy poniedziałek o 8:00
3. **Miesięczny raport finansowy** - pierwszego dnia miesiąca o 7:00

## Jak używać

### 1. Bezpośrednio z SDK

```python
from nlp2dsl_sdk import run_scheduled_report_demo

run_scheduled_report_demo()
```

### 2. Z terminala

```bash
./run.sh
# lub
python3 main.py
```

### 3. Co robi helper

```python
# 1. workflow_from_text("Codziennie o 9:00 generuj raport sprzedaży i wysyłaj do team@firma.pl")
# 2. run_workflow(name="daily_sales_report", trigger="daily", schedule="09:00", steps=[...])
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
