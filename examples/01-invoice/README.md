# Przykład: Wysyłanie Faktury

Podstawowy przykład pokazujący, jak wysłać fakturę za pomocą platformy NLP2DSL.

Ten katalog jest cienkim wrapperem nad `run_invoice_demo()` z pakietu `nlp2dsl_sdk`.

## Jak używać

### 1. Bezpośrednio z SDK

```python
from nlp2dsl_sdk import run_invoice_demo

run_invoice_demo()
```

### 2. Z terminala

```bash
./run.sh
# lub
python3 main.py
```

### 3. Co robi helper

```python
# 1. workflow_from_text("Wyślij fakturę na 1500 PLN do klient@firma.pl")
# 2. send_invoice(amount=1500, to="klient@firma.pl", currency="PLN")
```

## Oczekiwany wynik

System wygeneruje fakturę ID: `INV-YYYYMMDDHHMMSS` i wyśle ją na podany adres e-mail.

## Warianty

- "Wystaw rachunek na 200 EUR" - zmieni walutę
- "Faktura pro forma na 5000 PLN" - doda typ faktury (gdy obsługiwane)
- "Wyślij fakturę do wielu odbiorców" - obsługa listy e-maili (gdy obsługiwane)
