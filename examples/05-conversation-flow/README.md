# Przykład: Konwersacyjny Flow

Przykład integracji pokazujący pełny cykl konwersacyjny z platformą NLP2DSL - od zainicjowania rozmowy po wykonanie workflow.

Ten katalog jest cienkim wrapperem nad `ConversationFlow` z pakietu `nlp2dsl_sdk`.

## Scenariusz

Użytkownik chce wysłać fakturę, ale nie zna wszystkich wymaganych danych. System prowadzi go przez proces, dopytując o brakujące informacje.

## Flow konwersacji

1. **Użytkownik**: "Chcę wysłać fakturę"
2. **System**: "Podaj: kwotę, adres e-mail odbiorcy" + formularz
3. **Użytkownik**: "1500 PLN na klient@firma.pl"
4. **System**: "Workflow gotowy. Wyślij 'uruchom' aby wykonać."
5. **Użytkownik**: "uruchom"
6. **System**: "Workflow wykonany. Faktura ID: INV-..."

## Jak używać

### 1. Bezpośrednio z SDK

```python
from nlp2dsl_sdk import ConversationFlow

flow = ConversationFlow()
flow.run_demo()
```

### 2. Z terminala

```bash
./run.sh
# lub tryb interaktywny:
python3 main.py --interactive
```

## Zaawansowane funkcje konwersacji

### 1. Korekta danych

```bash
# Użytkownik może poprawić dane w każdej chwili:
python3 main.py --interactive
```

### 2. Dodawanie kroków

```bash
# Dodaj powiadomienie Slack do istniejącej faktury:
python3 main.py --interactive
```

### 3. Anulowanie

```bash
python3 main.py --interactive
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
