# Przykład: Konwersacyjny Flow

Przykład integracji pokazujący pełny cykl konwersacyjny z platformą NLP2DSL - od zainicjowania rozmowy po wykonanie workflow.

## Scenariusz

Użytkownik chce wysłać fakturę, ale nie zna wszystkich wymaganych danych. System prowadzi go przez proces, dopytując o brakujące informacje.

## Flow konwersacji

1. **Użytkownik**: "Chcę wysłać fakturę"
2. **System**: "Podaj: kwotę, adres e-mail odbiorcy" + formularz
3. **Użytkownik**: "1500 PLN na klient@firma.pl"
4. **System**: "Workflow gotowy. Wyślij 'uruchom' aby wykonać."
5. **Użytkownik**: "uruchom"
6. **System**: "Workflow wykonany. Faktura ID: INV-..."

## API Flow

### Krok 1: Rozpocznij rozmowę

```bash
curl -X POST http://localhost:8010/workflow/chat/start \
  -H "Content-Type: application/json" \
  -d '{"text": "Chcę wysłać fakturę"}'
```

Odpowiedź:
```json
{
  "conversation_id": "abc123def456",
  "status": "in_progress",
  "message": "Podaj: kwotę, adres e-mail odbiorcy",
  "missing": ["send_invoice.amount", "send_invoice.to"],
  "form": {
    "action": "send_invoice",
    "fields": [
      {"name": "amount", "type": "number", "label": "Kwota", "required": true},
      {"name": "to", "type": "email", "label": "Adres e-mail odbiorcy", "required": true},
      {"name": "currency", "type": "select", "label": "Waluta", "options": ["PLN","EUR","USD","GBP"]}
    ]
  }
}
```

### Krok 2: Uzupełnij dane

```bash
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc123def456", "text": "1500 PLN na klient@firma.pl"}'
```

Odpowiedź:
```json
{
  "conversation_id": "abc123def456",
  "status": "ready",
  "message": "Workflow gotowy: auto_send_invoice (1 kroków). Wyślij 'uruchom' aby wykonać.",
  "dsl": {
    "name": "auto_send_invoice",
    "steps": [
      {"action": "send_invoice", "config": {"amount": 1500, "to": "klient@firma.pl", "currency": "PLN"}}
    ]
  }
}
```

### Krok 3: Wykonaj workflow

```bash
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc123def456", "text": "uruchom"}'
```

Odpowiedź:
```json
{
  "conversation_id": "abc123def456",
  "status": "completed",
  "message": "Workflow auto_send_invoice uruchomiony.",
  "execution": {
    "workflow_id": "exec_789",
    "steps": [
      {
        "action": "send_invoice",
        "status": "completed",
        "result": {"invoice_id": "INV-20260406123456", "sent_to": "klient@firma.pl"}
      }
    ]
  }
}
```

## Uruchomienie przykładu

```bash
./run.sh
# lub
python3 main.py
```

## Zaawansowane funkcje konwersacji

### 1. Korekta danych

```bash
# Użytkownik może poprawić dane w każdej chwili
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "zmień kwotę na 2000 EUR"}'
```

### 2. Dodawanie kroków

```bash
# Dodaj powiadomienie Slack do istniejącej faktury
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "dodaj powiadomienie na #faktury"}'
```

### 3. Anulowanie

```bash
curl -X POST http://localhost:8010/workflow/chat/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "ID", "text": "anuluj"}'
```

## Słowa kluczowe

- Komendy wykonania: `uruchom`, `execute`, `wykonaj`, `start`, `run`
- Anulowanie: `anuluj`, `cancel`, `stop`
- Korekta: `zmień`, `popraw`, `zaktualizuj`
- Dodanie: `dodaj`, `plus`, `także`

## Integracja z frontendem

Formularz z odpowiedzi API może być bezpośrednio renderowany:

```javascript
// React przykład
function DynamicForm({ form }) {
  return (
    <form>
      {form.fields.map(field => (
        <div key={field.name}>
          <label>{field.label}</label>
          {field.type === 'select' ? (
            <select name={field.name}>
              {field.options.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : (
            <input 
              type={field.type} 
              name={field.name} 
              required={field.required}
            />
          )}
        </div>
      ))}
    </form>
  );
}
```
