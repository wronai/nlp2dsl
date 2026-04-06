<!-- code2docs:start --># nlp2dsl

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-158-green)
> **158** functions | **33** classes | **35** files | CC̄ = 3.3

> Auto-generated project documentation from source code analysis.

**Author:** Tom Softreck <tom@sapletta.com>  
**License:** MIT[(LICENSE)](./LICENSE)  
**Repository:** [https://github.com/wronai/nlp2dsl](https://github.com/wronai/nlp2dsl)

## Installation

### From PyPI

```bash
pip install nlp2dsl
```

### From Source

```bash
git clone https://github.com/wronai/nlp2dsl
cd nlp2dsl
pip install -e .
```


## Quick Start

### CLI Usage

```bash
# Generate full documentation for your project
nlp2dsl ./my-project

# Only regenerate README
nlp2dsl ./my-project --readme-only

# Preview what would be generated (no file writes)
nlp2dsl ./my-project --dry-run

# Check documentation health
nlp2dsl check ./my-project

# Sync — regenerate only changed modules
nlp2dsl sync ./my-project
```

### Python API

```python
from nlp2dsl import generate_readme, generate_docs, Code2DocsConfig

# Quick: generate README
generate_readme("./my-project")

# Full: generate all documentation
config = Code2DocsConfig(project_name="mylib", verbose=True)
docs = generate_docs("./my-project", config=config)
```

## Generated Output

When you run `nlp2dsl`, the following files are produced:

```
<project>/
├── README.md                 # Main project README (auto-generated sections)
├── docs/
│   ├── api.md               # Consolidated API reference
│   ├── modules.md           # Module documentation with metrics
│   ├── architecture.md      # Architecture overview with diagrams
│   ├── dependency-graph.md  # Module dependency graphs
│   ├── coverage.md          # Docstring coverage report
│   ├── getting-started.md   # Getting started guide
│   ├── configuration.md    # Configuration reference
│   └── api-changelog.md    # API change tracking
├── examples/
│   ├── quickstart.py       # Basic usage examples
│   └── advanced_usage.py   # Advanced usage examples
├── CONTRIBUTING.md         # Contribution guidelines
└── mkdocs.yml             # MkDocs site configuration
```

## Configuration

Create `nlp2dsl.yaml` in your project root (or run `nlp2dsl init`):

```yaml
project:
  name: my-project
  source: ./
  output: ./docs/

readme:
  sections:
    - overview
    - install
    - quickstart
    - api
    - structure
  badges:
    - version
    - python
    - coverage
  sync_markers: true

docs:
  api_reference: true
  module_docs: true
  architecture: true
  changelog: true

examples:
  auto_generate: true
  from_entry_points: true

sync:
  strategy: markers    # markers | full | git-diff
  watch: false
  ignore:
    - "tests/"
    - "__pycache__"
```

## Sync Markers

nlp2dsl can update only specific sections of an existing README using HTML comment markers:

```markdown
<!-- nlp2dsl:start -->
# Project Title
... auto-generated content ...
<!-- nlp2dsl:end -->
```

Content outside the markers is preserved when regenerating. Enable this with `sync_markers: true` in your configuration.

## Architecture

```
nlp2dsl/
├── project            ├── main    ├── app/        ├── main            ├── memory        ├── db/        ├── run            ├── postgres        ├── run        ├── main        ├── run        ├── main        ├── run        ├── workflow        ├── run        ├── main        ├── main        ├── main        ├── audio_parser        ├── registry        ├── parser_rules    ├── app/        ├── mapper        ├── orchestrator        ├── main        ├── system_executor        ├── schemas            ├── memory        ├── store/            ├── factory            ├── redis_store    ├── worker        ├── schemas        ├── settings        ├── parser_llm```

## API Overview

### Classes

- **`MemoryWorkflowRepo`** — —
- **`WorkflowRepo`** — Abstrakcja persystencji workflow.
- **`Base`** — —
- **`WorkflowRunModel`** — —
- **`PostgresWorkflowRepo`** — —
- **`ConversationFlow`** — Klasa do obsługi konwersacyjnego flow.
- **`StreamingSTT`** — Real-time streaming STT via Deepgram WebSocket.
- **`StepStatus`** — —
- **`Step`** — Pojedynczy krok workflow — deklaratywny opis akcji.
- **`RunWorkflowRequest`** — Żądanie uruchomienia workflow — DSL biznesowy.
- **`StepResult`** — —
- **`WorkflowResult`** — —
- **`ActionInfo`** — Opis dostępnej akcji (do listowania w GUI / API).
- **`MemoryConversationStore`** — —
- **`ConversationStore`** — Abstrakcja persystencji stanu konwersacji.
- **`RedisConversationStore`** — —
- **`NLPIntent`** — —
- **`NLPEntities`** — —
- **`NLPResult`** — —
- **`DSLStep`** — —
- **`WorkflowDSL`** — —
- **`DialogResponse`** — —
- **`NLPRequest`** — —
- **`ConversationState`** — Stan rozmowy — akumuluje dane między turami dialogu.
- **`FieldSchema`** — —
- **`ActionFormSchema`** — —
- **`ConversationResponse`** — —
- **`LLMSettings`** — —
- **`NLPSettings`** — —
- **`WorkerSettings`** — —
- **`FileAccessSettings`** — —
- **`SystemSettings`** — Pełny model ustawień systemu.
- **`SettingsManager`** — Runtime settings z persystencją do JSON.

### Functions

- `health()` — —
- `create_workflow_repo()` — Factory: zwraca Postgres repo jeśli URL jest ustawiony, inaczej memory.
- `main()` — Główna funkcja przykładu.
- `create_scheduled_report(name, report_type, trigger, schedule)` — Utwórz zaplanowany raport.
- `create_scheduled_from_text(text)` — Utwórz raport z tekstu zawierającego trigger.
- `main()` — Główna funkcja przykładu.
- `list_actions()` — Zwraca listę dostępnych akcji (DSL vocabulary).
- `run_workflow(req)` — Uruchamia workflow — iteruje po krokach DSL i deleguje
- `get_history()` — Zwraca historię wykonanych workflow.
- `get_workflow(workflow_id)` — Zwraca szczegóły konkretnego workflow.
- `workflow_from_text(body)` — Pełny pipeline: tekst → NLP → DSL → wykonanie.
- `chat_start(body)` — Rozpocznij konwersację AI → DSL.
- `chat_message(body)` — Kontynuuj konwersację — uzupełnij brakujące dane.
- `chat_get_state(conversation_id)` — Pobierz stan konwersacji.
- `actions_schema()` — Schematy formularzy UI — frontend generuje dynamicznie.
- `action_schema(action)` — Schemat formularza dla konkretnej akcji.
- `get_settings()` — Pokaż wszystkie ustawienia systemu.
- `get_settings_section(section)` — Pokaż ustawienia sekcji.
- `update_settings_section(section, body)` — Zaktualizuj ustawienia sekcji.
- `set_setting(body)` — Zmień ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}
- `reset_settings(body)` — Resetuj ustawienia.
- `system_execute(body)` — Wykonaj akcję systemową. Body: {"action": "system_file_list", "config": {}}
- `send_invoice(amount, to, currency)` — Wyślij fakturę przez API.
- `generate_invoice_from_text(text)` — Generuj DSL z języka naturalnego.
- `main()` — Główna funkcja przykładu.
- `send_email(to, subject, body)` — Wyślij e-mail przez API.
- `generate_email_from_text(text)` — Generuj DSL z języka naturalnego.
- `main()` — Główna funkcja przykładu.
- `generate_report_and_notify(report_type, format_type, email_to, slack_channel)` — Generuj raport i wyślij powiadomienia.
- `generate_composite_from_text(text)` — Generuj DSL z tekstu z wieloma akcjami.
- `main()` — Główna funkcja przykładu.
- `stt_audio(audio_bytes, language)` — Transcribe audio bytes to text using Deepgram HTTP API.
- `stt_file(file_path, language)` — Transcribe audio file to text using Deepgram.
- `is_stt_available()` — Check if STT is available (Deepgram configured).
- `get_action_by_alias(text)` — Dopasuj tekst do akcji po aliasach.
- `get_trigger(text)` — Wykryj trigger z tekstu.
- `get_required_fields(action)` — Zwróć wymagane pola dla akcji.
- `get_defaults(action)` — Zwróć domyślne wartości opcjonalnych pól.
- `parse_rules(text)` — Parse text using rules — no LLM needed.
- `map_to_dsl(nlp)` — Konwertuje NLPResult → WorkflowDSL.
- `start_conversation(text)` — Rozpocznij nową rozmowę od pierwszej wiadomości użytkownika.
- `continue_conversation(conversation_id, text)` — Kontynuuj istniejącą rozmowę — użytkownik uzupełnia brakujące dane.
- `get_conversation(conversation_id)` — Pobierz stan rozmowy.
- `get_action_form(action)` — Generuj formularz UI z registry (schema-driven UI).
- `parse_text(req)` — Etap 1: tekst → intent + entities.
- `text_to_dsl(req)` — Pełny pipeline: tekst → NLP → DSL.
- `list_actions()` — Zwraca rejestr akcji z aliasami (vocabulary DSL).
- `health()` — —
- `chat_start(text, audio)` — Rozpocznij nową konwersację. System rozpoznaje intencję i dopytuje o brakujące dane.
- `chat_message(conversation_id, text, audio)` — Kontynuuj rozmowę — uzupełnij brakujące dane.
- `chat_state(conversation_id)` — Pobierz aktualny stan konwersacji.
- `actions_schema()` — Zwraca pełny schemat formularzy dla wszystkich akcji.
- `action_schema(action)` — Zwraca schemat formularza dla konkretnej akcji.
- `get_settings()` — Pokaż wszystkie ustawienia systemu.
- `get_settings_section(section)` — Pokaż ustawienia sekcji (llm, nlp, worker, file_access).
- `update_settings_section(section, body)` — Zaktualizuj ustawienia sekcji.
- `set_setting(body)` — Zmień pojedyncze ustawienie. Body: {"path": "llm.model", "value": "gpt-4o"}
- `reset_settings(body)` — Resetuj ustawienia. Body: {"section": "llm"} lub {} dla wszystkich.
- `system_execute(body)` — Wykonaj akcję systemową bezpośrednio.
- `websocket_chat(websocket, conversation_id)` — WebSocket endpoint dla voice chat w czasie rzeczywistym.
- `chat_ui()` — Serwuj chat UI z voice support.
- `execute_system_action(action, config)` — Route and execute system action.
- `get_conversation_store()` — Singleton factory — zwraca store odpowiedni dla środowiska.
- `action(name)` — Dekorator rejestrujący handler akcji.
- `handle_send_invoice(config)` — —
- `handle_send_email(config)` — —
- `handle_generate_report(config)` — —
- `handle_crm_update(config)` — —
- `handle_notify_slack(config)` — —
- `execute_step(step)` — Wykonuje pojedynczy krok workflow.
- `health()` — —
- `parse_llm(text)` — Parse text using LLM via LiteLLM.


## Project Structure

📦 `backend.app`
📦 `backend.app.db` (6 functions, 1 classes)
📄 `backend.app.db.memory` (6 functions, 1 classes)
📄 `backend.app.db.postgres` (9 functions, 3 classes)
📄 `backend.app.main` (1 functions)
📄 `backend.app.schemas` (6 classes)
📄 `backend.app.workflow` (16 functions)
📄 `examples.01-invoice.main` (3 functions)
📄 `examples.01-invoice.run`
📄 `examples.02-email.main` (3 functions)
📄 `examples.02-email.run`
📄 `examples.03-report-and-notify.main` (3 functions)
📄 `examples.03-report-and-notify.run`
📄 `examples.04-scheduled-report.main` (3 functions)
📄 `examples.04-scheduled-report.run`
📄 `examples.05-conversation-flow.main` (7 functions, 1 classes)
📄 `examples.05-conversation-flow.run`
📦 `nlp-service.app`
📄 `nlp-service.app.audio_parser` (8 functions, 1 classes)
📄 `nlp-service.app.main` (18 functions)
📄 `nlp-service.app.mapper` (6 functions)
📄 `nlp-service.app.orchestrator` (7 functions)
📄 `nlp-service.app.parser_llm` (3 functions)
📄 `nlp-service.app.parser_rules` (5 functions)
📄 `nlp-service.app.registry` (4 functions)
📄 `nlp-service.app.schemas` (11 classes)
📄 `nlp-service.app.settings` (11 functions, 6 classes)
📦 `nlp-service.app.store` (4 functions, 1 classes)
📄 `nlp-service.app.store.factory` (1 functions)
📄 `nlp-service.app.store.memory` (5 functions, 1 classes)
📄 `nlp-service.app.store.redis_store` (7 functions, 1 classes)
📄 `nlp-service.app.system_executor` (13 functions)
📄 `project`
📄 `tauri-wrapper.src-tauri.src.main` (1 functions)
📄 `worker.worker` (8 functions)

## Requirements



## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Tom Sapletta <tom-sapletta-com@users.noreply.github.com>

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/wronai/nlp2dsl
cd nlp2dsl

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- 📖 [Full Documentation](https://github.com/wronai/nlp2dsl/tree/main/docs) — API reference, module docs, architecture
- 🚀 [Getting Started](https://github.com/wronai/nlp2dsl/blob/main/docs/getting-started.md) — Quick start guide
- 📚 [API Reference](https://github.com/wronai/nlp2dsl/blob/main/docs/api.md) — Complete API documentation
- 🔧 [Configuration](https://github.com/wronai/nlp2dsl/blob/main/docs/configuration.md) — Configuration options
- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `docs/api.md` | Consolidated API reference | [View](./docs/api.md) |
| `docs/modules.md` | Module reference with metrics | [View](./docs/modules.md) |
| `docs/architecture.md` | Architecture with diagrams | [View](./docs/architecture.md) |
| `docs/dependency-graph.md` | Dependency graphs | [View](./docs/dependency-graph.md) |
| `docs/coverage.md` | Docstring coverage report | [View](./docs/coverage.md) |
| `docs/getting-started.md` | Getting started guide | [View](./docs/getting-started.md) |
| `docs/configuration.md` | Configuration reference | [View](./docs/configuration.md) |
| `docs/api-changelog.md` | API change tracking | [View](./docs/api-changelog.md) |
| `CONTRIBUTING.md` | Contribution guidelines | [View](./CONTRIBUTING.md) |
| `examples/` | Usage examples | [Browse](./examples) |
| `mkdocs.yml` | MkDocs configuration | — |

<!-- code2docs:end -->