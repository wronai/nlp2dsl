# Przykład: Raport i Powiadomienia

Zaawansowany przykład pokazujący, jak zautomatyzować generowanie raportu i wysyłanie powiadomień do wielu kanałów.

Ten katalog jest cienkim wrapperem nad `run_report_and_notify_demo()` z pakietu `nlp2dsl_sdk`.

## Scenariusz

Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl oraz powiadomienie na Slack #sales

## Jak używać

### 1. Bezpośrednio z SDK

```python
from nlp2dsl_sdk import run_report_and_notify_demo

run_report_and_notify_demo()
```

### 2. Z terminala

```bash
./run.sh
# lub
python3 main.py
```

### 3. Co robi helper

```python
# 1. workflow_from_text("Co tydzień generuj raport sprzedaży w PDF i wyślij email do manager@firma.pl oraz powiadom na Slack #sales")
# 2. generate_report_and_notify(report_type="sales", format_type="pdf", email_to="manager@firma.pl", slack_channel="#sales", trigger="weekly")
```

## Oczekiwany wynik

1. Wygenerowany raport PDF sprzedaży
2. E-mail wysłany do manager@firma.pl z załącznikiem
3. Powiadomienie na kanale #sales Slack

## Warianty

- "Raport HR i powiadomienie na #hr" - zmienia typ raportu i kanał
- "Miesięczny raport finansów do CFO" - zmienia częstotliwość i odbiorcę
- "Generuj raport marketingowy i wyślij do teamu" - inny typ raportu
