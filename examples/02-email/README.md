# Przykład: Wysyłanie E-maila

Podstawowy przykład pokazujący, jak wysłać e-mail za pomocą platformy NLP2DSL.

Ten katalog jest cienkim wrapperem nad `run_email_demo()` z pakietu `nlp2dsl_sdk`.

## Jak używać

### 1. Bezpośrednio z SDK

```python
from nlp2dsl_sdk import run_email_demo

run_email_demo()
```

### 2. Z terminala

```bash
./run.sh
# lub
python3 main.py
```

### 3. Co robi helper

```python
# 1. workflow_from_text("Wyślij email do team@firma.pl z tematem Status projektu")
# 2. send_email(to="team@firma.pl", subject="Status dzienny projektów", body="...")
```

## Oczekiwany wynik

System wyśle e-mail na podany adres z określonym tematem i treścią.

## Warianty

- "Wyślij powiadomienie na admin@firma.pl" - alias "powiadomienie"
- "Maila do klient@firma.pl z ofertą" - alias "maila"
- "Napisz do zespołu o spotkaniu" - alias "napisz"
