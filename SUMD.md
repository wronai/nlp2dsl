# MVP Automation Platform

Reusable Python SDK for the NLP2DSL platform

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Interfaces](#interfaces)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Release Management (`goal.yaml`)](#release-management-goalyaml)
- [Makefile Targets](#makefile-targets)
- [Code Analysis](#code-analysis)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Intent](#intent)

## Metadata

- **name**: `nlp2dsl`
- **version**: `0.0.18`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, testql(4), app.doql.less, pyqual.yaml, goal.yaml, .env.example, docker-compose.yml, project/(3 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: nlp2dsl;
  version: 0.0.18;
}

dependencies {
  runtime: "requests>=2.31.0, pyyaml>=6.0";
}

entity[name="NLPIntent"] {
  intent: string!;
  confidence: float!;
}

entity[name="NLPEntities"] {
  amount: float | None;
  currency: str | None;
  to: str | None;
  email_to: str | None;
  subject: str | None;
  message: str | None;
  channel: str | None;
  chat_id: str | None;
  title: str | None;
  report_type: str | None;
  format: str | None;
  entity: str | None;
  data: dict | None;
  setting_path: str | None;
  setting_value: str | None;
  section: str | None;
  file_path: str | None;
  content: str | None;
  directory: str | None;
  pattern: str | None;
  line_start: int | None;
  line_end: int | None;
  mode: str | None;
  action_name: str | None;
  action_description: str | None;
  required_fields: list[str] | None;
  aliases: list[str] | None;
  description: str | None;
  language: str | None;
  context: str | None;
  include_tests: bool | None;
  shell_command: str | None;
}

entity[name="DSLStep"] {
  action: string!;
  config: json!;
}

entity[name="WorkflowDSL"] {
  name: string!;
  trigger: str | None;
  steps: list[DSLStep]!;
}

entity[name="ConversationState"] {
  id: string!;
  intent: str | None;
  entities: json!;
  missing: list[str]!;
  dsl: WorkflowDSL | None;
  status: string!;
  history: list[dict]!;
}

entity[name="Step"] {
  id: string!;
  action: string!;
  config: json!;
}

entity[name="ActionInfo"] {
  name: string!;
  description: string!;
  config_schema: json!;
}

database[name="postgres"] {
  type: postgresql;
  url: env.DATABASE_URL;
}

database[name="redis"] {
  type: redis;
  url: env.REDIS_URL;
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="nlp2dsl"] {

}

integration[name="nlp"] {
  type: api;
}

workflow[name="install"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -m pip install -e .;
}

workflow[name="install-dev"] {
  trigger: manual;
  step-1: depend target=setup-dev;
}

workflow[name="setup-dev"] {
  trigger: manual;
  step-1: run cmd=./scripts/setup-dev.sh;
}

workflow[name="update"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)==> update integration stack$(NC)";
  step-2: run cmd=./scripts/setup-dev.sh;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -m pytest tests/ -v;
}

workflow[name="check-pypi-deps"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -c "import build, twine" 2>/dev/null || $(PYTHON) -m pip install build twine -q;
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=rm -rf dist/ build/ *.egg-info;
  step-2: run cmd=for pkg in $(PACKAGES); do \;
  step-3: run cmd=rm -rf $$pkg/dist $$pkg/build $$pkg/src/*.egg-info 2>/dev/null || true; \;
  step-4: run cmd=done;
  step-5: run cmd=find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)==> build root SDK$(NC)";
  step-2: run cmd=$(PYTHON) -m build .;
}

workflow[name="build-packages"] {
  trigger: manual;
  step-1: run cmd=for pkg in $(PACKAGES); do \;
  step-2: run cmd=echo "$(YELLOW)==> build $$pkg$(NC)"; \;
  step-3: run cmd=$(PYTHON) -m build $$pkg; \;
  step-4: run cmd=done;
}

workflow[name="build-all"] {
  trigger: manual;
  step-1: depend target=build;
  step-2: depend target=build-packages;
}

workflow[name="publish-root"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)==> twine upload root SDK$(NC)";
  step-2: run cmd=$(PYTHON) -m twine upload dist/*;
}

workflow[name="publish-packages"] {
  trigger: manual;
  step-1: run cmd=for pkg in $(PACKAGES); do \;
  step-2: run cmd=echo "$(YELLOW)==> twine upload $$pkg$(NC)"; \;
  step-3: run cmd=$(PYTHON) -m twine upload --skip-existing $$pkg/dist/* || exit 1; \;
  step-4: run cmd=sleep $(PYPI_UPLOAD_DELAY); \;
  step-5: run cmd=done;
}

workflow[name="publish-package"] {
  trigger: manual;
  step-1: run cmd=test -n "$(PKG)" || (echo "Usage: make publish-package PKG=packages/nlp2dsl-show" && exit 1);
  step-2: run cmd=echo "$(YELLOW)==> build $(PKG)$(NC)";
  step-3: run cmd=$(PYTHON) -m build $(PKG);
  step-4: run cmd=echo "$(YELLOW)==> twine upload $(PKG)$(NC)";
  step-5: run cmd=$(PYTHON) -m twine upload --skip-existing $(PKG)/dist/*;
}

workflow[name="publish"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)==> Publishing nlp2dsl + packages to PyPI$(NC)";
  step-2: run cmd=$(PYTHON) -m twine upload dist/*;
  step-3: run cmd=for pkg in $(PACKAGES); do \;
  step-4: run cmd=echo "$(YELLOW)==> twine upload $$pkg$(NC)"; \;
  step-5: run cmd=$(PYTHON) -m twine upload $$pkg/dist/*; \;
  step-6: run cmd=done;
  step-7: run cmd=echo "$(GREEN)Done: nlp2dsl + $(words $(PACKAGES)) packages published$(NC)";
}

workflow[name="version"] {
  trigger: manual;
  step-1: run cmd=grep -m1 '^version = ' pyproject.toml | cut -d'"' -f2;
}

workflow[name="package-versions"] {
  trigger: manual;
  step-1: run cmd=for pkg in $(PACKAGES); do \;
  step-2: run cmd=v=$$(grep -m1 '^version = ' $$pkg/pyproject.toml | cut -d'"' -f2); \;
  step-3: run cmd=echo "$$pkg: $$v"; \;
  step-4: run cmd=done;
}

deploy {
  target: docker-compose;
  compose_file: docker-compose.yml;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  python_version: >=3.10;
}

environment[name="backup"] {
  runtime: docker-compose;
  env_file: .env.backup;
}
```

## Interfaces

### CLI Entry Points

- `nlp2dsl`
- `nlp2dsl-demo`

### testql Scenarios

#### `testql-scenarios/generated-api-smoke.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-api-smoke.testql.toon.yaml
# SCENARIO: Auto-generated API Smoke Tests
# TYPE: api
# GENERATED: true
# DETECTORS: FastAPIDetector, WebSocketDetector, ConfigEndpointDetector

CONFIG[5]{key, value}:
  base_url, http://localhost:8101
  timeout_ms, 10000
  retry_count, 3
  retry_backoff_ms, 1000
  detected_frameworks, FastAPIDetector, WebSocketDetector, ConfigEndpointDetector

# Wait for service to be ready
WAIT 1000

# Health check
API GET /api/health 200
ASSERT_STATUS 200

# REST API Endpoints (1 unique)
API[1]{method, endpoint, expected_status}:
  GET, /, 200

# Capture useful values from responses for subsequent tests
# CAPTURE request_id FROM 'headers.x-request-id'
# CAPTURE session_token FROM 'body.token'

ASSERT[2]{field, operator, expected}:
  _status, <, 500
  _status, >=, 200

# Conditional flow for error handling
FLOW[2]{condition, action}:
  _status >= 500, LOG 'Server error detected'
  _status == 429, WAIT 2000  # Rate limit - wait and retry


# Summary by Framework:
#   docker: 7 endpoints
```

#### `testql-scenarios/generated-cli-tests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-cli-tests.testql.toon.yaml
# SCENARIO: CLI Command Tests
# TYPE: cli
# GENERATED: true

CONFIG[2]{key, value}:
  cli_command, python -m nlp2dsl
  timeout_ms, 10000

# Test 1: CLI help command
SHELL "python -m nlp2dsl --help" 5000
ASSERT_EXIT_CODE 0
ASSERT_STDOUT_CONTAINS "usage"

# Test 2: CLI version command
SHELL "python -m nlp2dsl --version" 5000
ASSERT_EXIT_CODE 0

# Test 3: CLI main workflow (dry-run)
SHELL "python -m nlp2dsl --help" 10000
ASSERT_EXIT_CODE 0
```

#### `testql-scenarios/generated-examples.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-examples.testql.toon.yaml
# SCENARIO: NLP2DSL Examples (aggregated)
# TYPE: cli
# GENERATED: true
# PIPELINE: NLP → DSL → CMD → process

CONFIG[2]{key, value}:
  timeout_ms, 180000
  repo_root, .

# --- 01-invoice ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/01-invoice

# Run full example scenario
SHELL "cd examples/01-invoice && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: (no queries recorded)
SHELL "nlp2dsl run \"(no queries recorded)\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 02-email ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/02-email

# Run full example scenario
SHELL "cd examples/02-email && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij email do team@firma.pl z tematem Status dzienny proje
SHELL "nlp2dsl run \"Wyślij email do team@firma.pl z tematem Status dzienny projektów: Wszystkie projekty przebiegają zgodnie z harmonogramem.\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 03-report-and-notify ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/03-report-and-notify

# Run full example scenario
SHELL "cd examples/03-report-and-notify && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: (no queries recorded)
SHELL "nlp2dsl run \"(no queries recorded)\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 04-scheduled-report ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/04-scheduled-report

# Run full example scenario
SHELL "cd examples/04-scheduled-report && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: (no queries recorded)
SHELL "nlp2dsl run \"(no queries recorded)\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 05-conversation-flow ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/05-conversation-flow

# Run full example scenario
SHELL "cd examples/05-conversation-flow && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij fakturę na 500 PLN do test@firma.pl
SHELL "nlp2dsl run \"Wyślij fakturę na 500 PLN do test@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Powiadom #devops: backup gotowy
SHELL "nlp2dsl run \"Powiadom #devops: backup gotowy\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 3: znajdź pliki *.py w src
SHELL "nlp2dsl run \"znajdź pliki *.py w src\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 4: uruchom testy jednostkowe
SHELL "nlp2dsl run \"uruchom testy jednostkowe\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 5: pokaż status systemu
SHELL "nlp2dsl run \"pokaż status systemu\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 06-interactive-chat ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/06-interactive-chat

# Run full example scenario
SHELL "cd examples/06-interactive-chat && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij fakturę na 500 PLN do test@firma.pl
SHELL "nlp2dsl run \"Wyślij fakturę na 500 PLN do test@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Powiadom #devops: backup gotowy
SHELL "nlp2dsl run \"Powiadom #devops: backup gotowy\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 07-email-conversation ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/07-email-conversation

# Run full example scenario
SHELL "cd examples/07-email-conversation && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij email do jan@example.com z tematem Podsumowanie tygod
SHELL "nlp2dsl run \"Wyślij email do jan@example.com z tematem Podsumowanie tygodnia\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 08-multi-object-benchmark ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/08-multi-object-benchmark

# Run full example scenario
SHELL "cd examples/08-multi-object-benchmark && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wystaw fakturę na 3200 PLN do dostawca@firma.pl
SHELL "nlp2dsl run \"Wystaw fakturę na 3200 PLN do dostawca@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Invoice for 890 USD to billing@corp.com
SHELL "nlp2dsl run \"Invoice for 890 USD to billing@corp.com\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 3: Wyślij powiadomienie na Slack #devops: deploy produkcji zako
SHELL "nlp2dsl run \"Wyślij powiadomienie na Slack #devops: deploy produkcji zakończony\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 4: Notify Telegram chat -1001234567890: serwer API nie odpowiad
SHELL "nlp2dsl run \"Notify Telegram chat -1001234567890: serwer API nie odpowiada\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 5: Wyślij na Microsoft Teams kanał general: spotkanie sprint re
SHELL "nlp2dsl run \"Wyślij na Microsoft Teams kanał general: spotkanie sprint review jutro 10:00\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 6: Zaktualizuj lead w CRM: firma ACME, status qualified, owner 
SHELL "nlp2dsl run \"Zaktualizuj lead w CRM: firma ACME, status qualified, owner Jan Kowalski\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 7: Generuj raport marketingowy w CSV
SHELL "nlp2dsl run \"Generuj raport marketingowy w CSV\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 8: Co tydzień raport HR w formacie xlsx
SHELL "nlp2dsl run \"Co tydzień raport HR w formacie xlsx\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 9: Wyślij fakturę 1500 PLN do klient@firma.pl i powiadom #billi
SHELL "nlp2dsl run \"Wyślij fakturę 1500 PLN do klient@firma.pl i powiadom #billing na Slacku\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 10: Miesięczny raport finansów PDF i wyślij email do cfo@firma.p
SHELL "nlp2dsl run \"Miesięczny raport finansów PDF i wyślij email do cfo@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 11: Napisz w Pythonie funkcję obliczającą medianę listy liczb z 
SHELL "nlp2dsl run \"Napisz w Pythonie funkcję obliczającą medianę listy liczb z testami\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 12: Pokaż status systemu i wersję
SHELL "nlp2dsl run \"Pokaż status systemu i wersję\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 13: Jakie akcje biznesowe są dostępne?
SHELL "nlp2dsl run \"Jakie akcje biznesowe są dostępne?\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 14: Przypomnij dev@firma.pl o code review PR-442
SHELL "nlp2dsl run \"Przypomnij dev@firma.pl o code review PR-442\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 15: Powiadom kanał #sales o podpisaniu umowy z klientem Beta Cor
SHELL "nlp2dsl run \"Powiadom kanał #sales o podpisaniu umowy z klientem Beta Corp\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 16: Raport kwartalny sprzedaży CSV i wyślij go na #analytics
SHELL "nlp2dsl run \"Raport kwartalny sprzedaży CSV i wyślij go na #analytics\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 17: Dodaj kontakt do CRM typ contact z emailem anna@firma.pl
SHELL "nlp2dsl run \"Dodaj kontakt do CRM typ contact z emailem anna@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 18: Przygotuj raport finansowy PDF na koniec miesiąca
SHELL "nlp2dsl run \"Przygotuj raport finansowy PDF na koniec miesiąca\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 19: Napisz do hr@firma.pl: wniosek urlopowy został zaakceptowany
SHELL "nlp2dsl run \"Napisz do hr@firma.pl: wniosek urlopowy został zaakceptowany\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 20: Pełny flow: faktura 12000 PLN do enterprise@corp.com, email 
SHELL "nlp2dsl run \"Pełny flow: faktura 12000 PLN do enterprise@corp.com, email do ksiegowosc@firma.pl i Slack #finance\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 21: Wystaw fakturę na 3200 PLN do dostawca@firma.pl
SHELL "nlp2dsl run \"Wystaw fakturę na 3200 PLN do dostawca@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 22: Invoice for 890 USD to billing@corp.com
SHELL "nlp2dsl run \"Invoice for 890 USD to billing@corp.com\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 23: Wyślij powiadomienie na Slack #devops: deploy produkcji zako
SHELL "nlp2dsl run \"Wyślij powiadomienie na Slack #devops: deploy produkcji zakończony\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 24: Notify Telegram chat -1001234567890: serwer API nie odpowiad
SHELL "nlp2dsl run \"Notify Telegram chat -1001234567890: serwer API nie odpowiada\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 25: Wyślij na Microsoft Teams kanał general: spotkanie sprint re
SHELL "nlp2dsl run \"Wyślij na Microsoft Teams kanał general: spotkanie sprint review jutro 10:00\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 26: Zaktualizuj lead w CRM: firma ACME, status qualified, owner 
SHELL "nlp2dsl run \"Zaktualizuj lead w CRM: firma ACME, status qualified, owner Jan Kowalski\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 27: Generuj raport marketingowy w CSV
SHELL "nlp2dsl run \"Generuj raport marketingowy w CSV\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 28: Co tydzień raport HR w formacie xlsx
SHELL "nlp2dsl run \"Co tydzień raport HR w formacie xlsx\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 29: Wyślij fakturę 1500 PLN do klient@firma.pl i powiadom #billi
SHELL "nlp2dsl run \"Wyślij fakturę 1500 PLN do klient@firma.pl i powiadom #billing na Slacku\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 30: Miesięczny raport finansów PDF i wyślij email do cfo@firma.p
SHELL "nlp2dsl run \"Miesięczny raport finansów PDF i wyślij email do cfo@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 31: Napisz w Pythonie funkcję obliczającą medianę listy liczb z 
SHELL "nlp2dsl run \"Napisz w Pythonie funkcję obliczającą medianę listy liczb z testami\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 32: Pokaż status systemu i wersję
SHELL "nlp2dsl run \"Pokaż status systemu i wersję\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 33: Jakie akcje biznesowe są dostępne?
SHELL "nlp2dsl run \"Jakie akcje biznesowe są dostępne?\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 34: Przypomnij dev@firma.pl o code review PR-442
SHELL "nlp2dsl run \"Przypomnij dev@firma.pl o code review PR-442\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 35: Powiadom kanał #sales o podpisaniu umowy z klientem Beta Cor
SHELL "nlp2dsl run \"Powiadom kanał #sales o podpisaniu umowy z klientem Beta Corp\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 36: Raport kwartalny sprzedaży CSV i wyślij go na #analytics
SHELL "nlp2dsl run \"Raport kwartalny sprzedaży CSV i wyślij go na #analytics\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 37: Dodaj kontakt do CRM typ contact z emailem anna@firma.pl
SHELL "nlp2dsl run \"Dodaj kontakt do CRM typ contact z emailem anna@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 38: Przygotuj raport finansowy PDF na koniec miesiąca
SHELL "nlp2dsl run \"Przygotuj raport finansowy PDF na koniec miesiąca\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 39: Napisz do hr@firma.pl: wniosek urlopowy został zaakceptowany
SHELL "nlp2dsl run \"Napisz do hr@firma.pl: wniosek urlopowy został zaakceptowany\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 40: Pełny flow: faktura 12000 PLN do enterprise@corp.com, email 
SHELL "nlp2dsl run \"Pełny flow: faktura 12000 PLN do enterprise@corp.com, email do ksiegowosc@firma.pl i Slack #finance\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 09-execution-smoke ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/09-execution-smoke

# Run full example scenario
SHELL "cd examples/09-execution-smoke && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij fakturę na 500 PLN do test@firma.pl
SHELL "nlp2dsl run \"Wyślij fakturę na 500 PLN do test@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Powiadom #devops: backup gotowy
SHELL "nlp2dsl run \"Powiadom #devops: backup gotowy\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 10-llm-benchmark ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/10-llm-benchmark

# Run full example scenario
SHELL "cd examples/10-llm-benchmark && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij fakturę na 500 PLN do test@firma.pl
SHELL "nlp2dsl run \"Wyślij fakturę na 500 PLN do test@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Powiadom #devops: backup gotowy
SHELL "nlp2dsl run \"Powiadom #devops: backup gotowy\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 11-notify-quality ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/11-notify-quality

# Run full example scenario
SHELL "cd examples/11-notify-quality && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Powiadom #oncall
SHELL "nlp2dsl run \"Powiadom #oncall\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Wyślij powiadomienie na Slack #devops: deploy zakończony
SHELL "nlp2dsl run \"Wyślij powiadomienie na Slack #devops: deploy zakończony\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 3: Powiadom kanał #sales o podpisaniu umowy z Beta Corp
SHELL "nlp2dsl run \"Powiadom kanał #sales o podpisaniu umowy z Beta Corp\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 4: Notify Telegram chat -1001234567890: API timeout na produkcj
SHELL "nlp2dsl run \"Notify Telegram chat -1001234567890: API timeout na produkcji\" --json" 30000
ASSERT_EXIT_CODE 0

# --- 12-ir-show ---
# PIPELINE: NLP → DSL → CMD → process

CONFIG[3]{key, value}:
  cli_command, python3 main.py
  timeout_ms, 120000
  example_dir, examples/12-ir-show

# Run full example scenario
SHELL "cd examples/12-ir-show && python3 main.py" 120000
ASSERT_EXIT_CODE 0

# Query 1: Wyślij fakturę na 500 PLN do test@firma.pl
SHELL "nlp2dsl run \"Wyślij fakturę na 500 PLN do test@firma.pl\" --json" 30000
ASSERT_EXIT_CODE 0

# Query 2: Powiadom #devops: backup gotowy
SHELL "nlp2dsl run \"Powiadom #devops: backup gotowy\" --json" 30000
ASSERT_EXIT_CODE 0
```

#### `testql-scenarios/generated-from-pytests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-from-pytests.testql.toon.yaml
# SCENARIO: Auto-generated from Python Tests
# TYPE: integration
# GENERATED: true

CONFIG[2]{key, value}:
  base_url, ${api_url:-http://localhost:8101}
  timeout_ms, 10000

# Converted 118 assertions from pytest
ASSERT[118]{field, operator, expected}:
  client.backend_url, ==, "http://backend.env"
  client.nlp_service_url, ==, "http://nlp.env"
  client.worker_url, ==, "http://worker.env"
  client.timeout, ==, 12.5
  generated.status, ==, "complete"
  execution.status, ==, "completed"
  start.conversation_id, ==, "conv-1"
  message.conversation_id, ==, "conv-1"
  schema.action, ==, "send_invoice"
  schema.fields[0].name, ==, "to"
  session.calls[0][1], ==, "http://backend.test/workflow/from-text"
  session.calls[0][2].json, ==, {"text": "Wyślij fakturę"
  session.calls[1][1], ==, "http://backend.test/workflow/run"
  session.calls[1][2].json.steps[0].config.amount, ==, 1500.0
  session.calls[1][2].json.steps[0].config.to, ==, "klient@firma.pl"
  session.calls[2][1], ==, "http://backend.test/workflow/chat/start"
  session.calls[2][2].json, ==, {"text": "Chcę wysłać fakturę"}
  session.calls[3][1], ==, "http://backend.test/workflow/chat/message"
  session.calls[3][2].json, ==, {"conversation_id": "conv-1"
  session.calls[4][1], ==, "http://backend.test/workflow/actions/schema/send_invoice"
  workflow_step("notify_slack", channel="#ops", message="Deploy done"), ==, {
  crm_result.status, ==, "completed"
  slack_result.status, ==, "completed"
  invoice_result.status, ==, "completed"
  session.calls[0][1], ==, "http://backend.test/workflow/run"
  session.calls[0][2].json.steps[0].action, ==, "crm_update"
  session.calls[0][2].json.steps[0].config.entity, ==, "lead"
  session.calls[1][2].json.steps[0].action, ==, "notify_slack"
  session.calls[1][2].json.steps[0].config.channel, ==, "#ops"
  invoice_payload.name, ==, "invoice_notification_workflow"
  [step.action for step in invoice_payload.steps], ==, [
  invoice_payload.steps[1].config.to, ==, "billing@firma.pl"
  invoice_payload.steps[2].config.channel, ==, "#finance"
  direct.language, ==, "python"
  conversation.conversation_id, ==, "conv-2"
  continuation.conversation_id, ==, "conv-2"
  worker.status, ==, "completed"
  session.calls[0][1], ==, "http://nlp.test/code/generate"
  session.calls[1][1], ==, "http://nlp.test/code/languages"
  session.calls[2][1], ==, "http://nlp.test/chat/start"
  session.calls[2][2].data, ==, {"text": "Chcę napisać program w Javie"}
  session.calls[3][1], ==, "http://nlp.test/chat/message"
  session.calls[3][2].data, ==, {"conversation_id": "conv-2"
  session.calls[4][1], ==, "http://worker.test/execute"
  session.calls[4][2].json.action, ==, "generate_code"
  session.calls[4][2].json.config.language, ==, "cpp"
  health.backend.service, ==, "backend"
  health.nlp_service.service, ==, "nlp-service"
  health.worker.service, ==, "worker"
  session.calls[0][1], ==, "http://backend.test/health"
  session.calls[1][1], ==, "http://nlp.test/health"
  session.calls[2][1], ==, "http://worker.test/health"
  dialog.status, ==, "incomplete"
  s.worker_url, ==, "http://worker:8000"
  s.nlp_service_url, ==, "http://nlp-service:8002"
  s.worker_url, ==, "http://custom-worker:9000"
  s.worker_url, ==, "http://worker:8000"
  s.nlp_service_url, ==, "http://nlp-service:8002"
  s.worker_url, ==, "http://custom-worker:9000"
  client.backend_url, ==, "http://backend.env"
  client.nlp_service_url, ==, "http://nlp.env"
  client.worker_url, ==, "http://worker.env"
  client.timeout, ==, 12.5
  generated.status, ==, "complete"
  execution.status, ==, "completed"
  start.conversation_id, ==, "conv-1"
  message.conversation_id, ==, "conv-1"
  schema.action, ==, "send_invoice"
  schema.fields[0].name, ==, "to"
  session.calls[0][1], ==, "http://backend.test/workflow/from-text"
  session.calls[0][2].json, ==, {"text": "Wyślij fakturę"
  session.calls[1][1], ==, "http://backend.test/workflow/run"
  session.calls[1][2].json.steps[0].config.amount, ==, 1500.0
  session.calls[1][2].json.steps[0].config.to, ==, "klient@firma.pl"
  session.calls[2][1], ==, "http://backend.test/workflow/chat/start"
  session.calls[2][2].json, ==, {"text": "Chcę wysłać fakturę"}
  session.calls[3][1], ==, "http://backend.test/workflow/chat/message"
  session.calls[3][2].json, ==, {"conversation_id": "conv-1"
  session.calls[4][1], ==, "http://backend.test/workflow/actions/schema/send_invoice"
  workflow_step("notify_slack", channel="#ops", message="Deploy done"), ==, {
  crm_result.status, ==, "completed"
  slack_result.status, ==, "completed"
  invoice_result.status, ==, "completed"
  session.calls[0][1], ==, "http://backend.test/workflow/run"
  session.calls[0][2].json.steps[0].action, ==, "crm_update"
  session.calls[0][2].json.steps[0].config.entity, ==, "lead"
  session.calls[1][2].json.steps[0].action, ==, "notify_slack"
  session.calls[1][2].json.steps[0].config.channel, ==, "#ops"
  invoice_payload.name, ==, "invoice_notification_workflow"
  [step.action for step in invoice_payload.steps], ==, [
  invoice_payload.steps[1].config.to, ==, "billing@firma.pl"
  invoice_payload.steps[2].config.channel, ==, "#finance"
  direct.language, ==, "python"
  conversation.conversation_id, ==, "conv-2"
  continuation.conversation_id, ==, "conv-2"
  worker.status, ==, "completed"
  session.calls[0][1], ==, "http://nlp.test/code/generate"
  session.calls[1][1], ==, "http://nlp.test/code/languages"
  session.calls[2][1], ==, "http://nlp.test/chat/start"
  session.calls[2][2].data, ==, {"text": "Chcę napisać program w Javie"}
  session.calls[3][1], ==, "http://nlp.test/chat/message"
  session.calls[3][2].data, ==, {"conversation_id": "conv-2"
  session.calls[4][1], ==, "http://worker.test/execute"
  session.calls[4][2].json.action, ==, "generate_code"
  session.calls[4][2].json.config.language, ==, "cpp"
  health.backend.service, ==, "backend"
  health.nlp_service.service, ==, "nlp-service"
  health.worker.service, ==, "worker"
  session.calls[0][1], ==, "http://backend.test/health"
  session.calls[1][1], ==, "http://nlp.test/health"
  session.calls[2][1], ==, "http://worker.test/health"
  s.worker_url, ==, "http://worker:8000"
  s.nlp_service_url, ==, "http://nlp-service:8002"
  s.worker_url, ==, "http://custom-worker:9000"
  s.worker_url, ==, "http://worker:8000"
  s.nlp_service_url, ==, "http://nlp-service:8002"
  s.worker_url, ==, "http://custom-worker:9000"
  dialog.status, ==, "incomplete"
```

## Workflows

## Quality Pipeline (`pyqual.yaml`)

```yaml markpact:pyqual path=pyqual.yaml
pipeline:
  profile: python-minimal

  # Override metrics (profile defaults: cc_max=15, critical_max=0):
  metrics:
    critical_max: 5

  # Explicit stages matching the python-minimal profile.
  stages:
    - name: analyze
      tool: code2llm-filtered
      optional: true
      timeout: 0

    - name: validate
      tool: vallm-filtered
      optional: true
      timeout: 0

    - name: lint
      tool: ruff
      optional: true

    - name: prefact
      tool: prefact
      optional: true
      timeout: 900

    - name: fix
      tool: llx-fix
      optional: true
      timeout: 1800

    - name: test
      run: bash .pfix-test-wrapper.sh

  # If you want to tighten gates later, add more overrides here.

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
```

## Configuration

```yaml
project:
  name: nlp2dsl
  version: 0.0.18
  env: local
```

## Dependencies

### Runtime

```text markpact:deps python
requests>=2.31.0
pyyaml>=6.0
```

## Deployment

```bash markpact:run
pip install nlp2dsl

# development install
pip install -e .[dev]
```

### Docker Compose (`docker-compose.yml`)

- **backend** image=`./backend` ports: `${NLP2DSL_BACKEND_HOST_PORT:-8010}:8000`
- **nlp-service** image=`./nlp-service` ports: `${NLP2DSL_NLP_HOST_PORT:-8012}:8002`
- **worker** image=`./worker` ports: `${NLP2DSL_WORKER_HOST_PORT:-8004}:8000`
- **postgres** image=`postgres:16-alpine`
- **redis** image=`redis:7-alpine`

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `*(not set)*` | ── OpenRouter (domyślny) ──────────────────────────────────── |
| `LLM_MODEL` | `openrouter/openai/gpt-5-mini` | NLP_ENRICH_MISSING=1 |
| `LLM_TEMPERATURE` | `0` | ── LLM Settings ───────────────────────────────────────────── |
| `LLM_MAX_TOKENS` | `1024` |  |
| `LLM_FALLBACK_THRESHOLD` | `0.5` |  |
| `NLP2DSL_BACKEND_HOST_PORT` | `8010` | 8002 jest zajęty przez Mullm Projector, gdy oba stacki działają równolegle. |
| `NLP2DSL_NLP_HOST_PORT` | `8012` |  |
| `NLP2DSL_WORKER_HOST_PORT` | `8004` |  |
| `NLP2DSL_CONFIG` | `./nlp2dsl.yaml` |  |
| `NLP2DSL_AGENT_ID` | `user` |  |
| `DEEPGRAM_API_KEY` | `*(not set)*` | Zdobądź klucz: https://console.deepgram.com/ |

## Release Management (`goal.yaml`)

- **versioning**: `semver`
- **commits**: `conventional` scope=`nlp2dsl`
- **changelog**: `keep-a-changelog`
- **build strategies**: `python`, `nodejs`, `rust`
- **version files**: `VERSION`, `pyproject.toml:version`, `venv/lib/python3.13/site-packages/cryptography/__init__.py:__version__`

## Makefile Targets

- `PACKAGES`
- `GREEN`
- `YELLOW`
- `BLUE`
- `NC`
- `help`
- `install`
- `install-dev`
- `setup-dev`
- `update`
- `test`
- `check-pypi-deps`
- `clean`
- `build`
- `build-packages`
- `build-all`
- `publish-root`
- `publish-packages`
- `publish-package`
- `publish`
- `version`
- `package-versions`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# nlp2dsl | 220f 20642L | python:197,shell:17,javascript:3,rust:2,less:1 | 2026-06-05
# stats: 543 func | 165 cls | 220 mod | CC̄=3.8 | critical:37 | cycles:0
# alerts[5]: CC _apply_context_filters=21; CC _build_config=19; CC resolve_intent=18; CC build_process_trace=17; CC test_workflow_and_conversation_endpoints=17
# hotspots[5]: process_example fan=24; _execute_workflow fan=19; enrich_entities fan=19; main fan=18; resolve_intent fan=17
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[220]:
  .pfix-test-wrapper.sh,16
  app.doql.less,234
  backend/app/__init__.py,1
  backend/app/config.py,43
  backend/app/db/__init__.py,50
  backend/app/db/memory.py,38
  backend/app/db/postgres.py,173
  backend/app/engine.py,270
  backend/app/logging_setup.py,101
  backend/app/main.py,49
  backend/app/routers/__init__.py,1
  backend/app/routers/chat.py,125
  backend/app/routers/settings.py,82
  backend/app/routers/system.py,30
  backend/app/routers/workflow.py,200
  backend/app/schemas.py,65
  backend/app/workflow.py,23
  backend/app/workflow_events.py,92
  backend/tests/__init__.py,1
  backend/tests/conftest.py,32
  backend/tests/test_config.py,83
  backend/tests/test_logging.py,124
  backend/tests/test_persistence.py,185
  backend/tests/test_workflow_api.py,267
  examples/01-invoice/main.py,34
  examples/01-invoice/run.sh,7
  examples/01-invoice/scenario.py,49
  examples/02-email/main.py,34
  examples/02-email/run.sh,7
  examples/02-email/scenario.py,58
  examples/03-report-and-notify/main.py,34
  examples/03-report-and-notify/run.sh,7
  examples/03-report-and-notify/scenario.py,59
  examples/04-scheduled-report/main.py,34
  examples/04-scheduled-report/run.sh,7
  examples/04-scheduled-report/scenario.py,61
  examples/05-conversation-flow/main.py,34
  examples/05-conversation-flow/run.sh,7
  examples/05-conversation-flow/scenario.py,45
  examples/06-interactive-chat/main.py,34
  examples/06-interactive-chat/scenario.py,46
  examples/07-email-conversation/main.py,34
  examples/07-email-conversation/scenario.py,37
  examples/08-multi-object-benchmark/benchmark_queries.py,159
  examples/08-multi-object-benchmark/main.py,34
  examples/08-multi-object-benchmark/scenario.py,138
  examples/09-execution-smoke/main.py,34
  examples/09-execution-smoke/scenario.py,45
  examples/10-llm-benchmark/main.py,34
  examples/10-llm-benchmark/scenario.py,38
  examples/11-notify-quality/main.py,34
  examples/11-notify-quality/scenario.py,50
  examples/12-ir-show/main.py,34
  examples/12-ir-show/scenario.py,89
  examples/basic/invoice/run.sh,1
  examples/bootstrap.py,27
  examples/code_generation_examples.py,26
  examples/run-all.sh,54
  metrun-profile.sh,49
  nlp-service/app/__init__.py,1
  nlp-service/app/access/__init__.py,16
  nlp-service/app/access/bootstrap.py,4
  nlp-service/app/access/config.py,4
  nlp-service/app/access/native.py,4
  nlp-service/app/access/policy.py,4
  nlp-service/app/access/uri_match.py,4
  nlp-service/app/audio_parser.py,149
  nlp-service/app/code_generator.py,280
  nlp-service/app/config.py,61
  nlp-service/app/conversation/__init__.py,14
  nlp-service/app/conversation/merge.py,37
  nlp-service/app/conversation/orchestrator.py,108
  nlp-service/app/conversation/responses.py,283
  nlp-service/app/dsl/__init__.py,5
  nlp-service/app/dsl/forms.py,92
  nlp-service/app/dsl/mapper.py,237
  nlp-service/app/dsl/pipeline.py,32
  nlp-service/app/execution/__init__.py,15
  nlp-service/app/execution/delegate.py,30
  nlp-service/app/execution/system.py,343
  nlp-service/app/governance/__init__.py,15
  nlp-service/app/governance/bootstrap.py,79
  nlp-service/app/governance/config.py,166
  nlp-service/app/governance/policy.py,303
  nlp-service/app/governance/uri_match.py,43
  nlp-service/app/logging_setup.py,101
  nlp-service/app/main.py,571
  nlp-service/app/mapper.py,6
  nlp-service/app/orchestrator.py,22
  nlp-service/app/parser_enrich.py,16
  nlp-service/app/parser_llm.py,6
  nlp-service/app/parser_rules.py,6
  nlp-service/app/parsing/__init__.py,4
  nlp-service/app/parsing/facade.py,6
  nlp-service/app/registry.py,404
  nlp-service/app/routing/__init__.py,18
  nlp-service/app/routing/intent.py,56
  nlp-service/app/routing/native.py,144
  nlp-service/app/routing/observability.py,58
  nlp-service/app/routing/orientation.py,380
  nlp-service/app/routing/parser/__init__.py,4
  nlp-service/app/routing/parser/enrich.py,142
  nlp-service/app/routing/parser/facade.py,20
  nlp-service/app/routing/parser/llm.py,146
  nlp-service/app/routing/parser/prompt_catalog.py,83
  nlp-service/app/routing/parser/resolve_mode.py,48
  nlp-service/app/routing/parser/rules.py,565
  nlp-service/app/routing/resolve.py,195
  nlp-service/app/schemas.py,138
  nlp-service/app/settings.py,252
  nlp-service/app/store/__init__.py,31
  nlp-service/app/store/factory.py,47
  nlp-service/app/store/memory.py,24
  nlp-service/app/store/redis_store.py,59
  nlp-service/app/system_executor.py,36
  nlp-service/integrations/__init__.py,6
  nlp-service/integrations/loader.py,63
  nlp-service/integrations/mullm/__init__.py,2
  nlp-service/integrations/mullm/registry.py,67
  nlp-service/tests/__init__.py,1
  nlp-service/tests/conftest.py,102
  nlp-service/tests/test_access.py,75
  nlp-service/tests/test_enrich.py,138
  nlp-service/tests/test_execution_delegate.py,25
  nlp-service/tests/test_mapper.py,295
  nlp-service/tests/test_orchestrator.py,250
  nlp-service/tests/test_orientation.py,107
  nlp-service/tests/test_parser_rules.py,314
  nlp-service/tests/test_registry.py,169
  nlp-service/tests/test_routing_observability.py,42
  nlp-service/tests/test_routing_resolve.py,62
  nlp-service/tests/test_store.py,193
  nlp-service/tests/test_system_executor.py,422
  nlp2dsl_sdk/__init__.py,38
  nlp2dsl_sdk/__main__.py,46
  nlp2dsl_sdk/artifacts.py,411
  nlp2dsl_sdk/cli.py,229
  nlp2dsl_sdk/client.py,601
  nlp2dsl_sdk/demos.py,355
  nlp2dsl_sdk/encoding.py,93
  nlp2dsl_sdk/example_loader.py,40
  nlp2dsl_sdk/preview.py,209
  packages/install-dev.sh,26
  packages/nlp2cmd-intent/src/nlp2cmd_intent/__init__.py,32
  packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py,38
  packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py,68
  packages/nlp2cmd-intent/src/nlp2cmd_intent/domain_mapping.py,44
  packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py,55
  packages/nlp2cmd-intent/src/nlp2cmd_intent/input.py,35
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/__init__.py,13
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py,1210
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py,229
  packages/nlp2cmd-intent/src/nlp2cmd_intent/nlp2cmd_convert.py,48
  packages/nlp2cmd-intent/src/nlp2cmd_intent/normalize.py,17
  packages/nlp2cmd-intent/src/nlp2cmd_intent/protocols.py,16
  packages/nlp2cmd-intent/tests/test_analyze_query.py,14
  packages/nlp2cmd-intent/tests/test_clarification.py,32
  packages/nlp2cmd-intent/tests/test_intent_pipeline.py,9
  packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py,44
  packages/nlp2cmd-planner/src/nlp2cmd_planner/__init__.py,16
  packages/nlp2cmd-planner/src/nlp2cmd_planner/pipeline.py,25
  packages/nlp2cmd-planner/src/nlp2cmd_planner/router.py,37
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/__init__.py,1
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rest_workflow.py,83
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rule_shell.py,75
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategy.py,16
  packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py,51
  packages/nlp2cmd-planner/tests/test_planning_pipeline.py,53
  packages/nlp2cmd-planner/tests/test_rest_workflow.py,91
  packages/nlp2cmd-planner/tests/test_rest_workflow_propact.py,34
  packages/nlp2cmd-propact/src/nlp2cmd_propact/__init__.py,17
  packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py,135
  packages/nlp2cmd-propact/src/nlp2cmd_propact/cli.py,23
  packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py,156
  packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py,195
  packages/nlp2cmd-propact/tests/test_adapter.py,140
  packages/nlp2cmd-propact/tests/test_executor.py,79
  packages/nlp2cmd-propact/tests/test_runner.py,126
  packages/nlp2dsl-show/src/nlp2dsl_show/__init__.py,4
  packages/nlp2dsl-show/src/nlp2dsl_show/cli.py,92
  packages/nlp2dsl-show/src/nlp2dsl_show/encoding.py,45
  packages/nlp2dsl-show/tests/test_cli.py,48
  packages/pact-ir/src/pact_ir/__init__.py,18
  packages/pact-ir/src/pact_ir/execution_plan.py,60
  packages/pact-ir/src/pact_ir/intent.py,45
  packages/pact-ir/src/pact_ir/target_kind.py,35
  packages/pact-ir/tests/test_ir_roundtrip.py,37
  project.sh,59
  run-all-tests.sh,45
  scripts/aggregate-example-testql.py,50
  scripts/publish-all.sh,45
  scripts/run-example-testql-results.py,365
  scripts/setup-dev.sh,44
  tauri-wrapper/desktop.sh,80
  tauri-wrapper/scripts/dev.js,57
  tauri-wrapper/scripts/serve-dist.js,140
  tauri-wrapper/src-tauri/build.rs,4
  tauri-wrapper/src-tauri/src/main.rs,8
  tauri-wrapper/test/mvp-voice-chat-wrapper.test.js,9
  test_code_generation.py,140
  tests/conftest.py,11
  tests/e2e/__init__.py,1
  tests/e2e/conftest.py,129
  tests/e2e/test_backend.py,152
  tests/e2e/test_chat_ui.py,263
  tests/e2e/test_nlp_service.py,216
  tests/e2e/test_websocket.py,112
  tests/run.sh,86
  tests/test_encoding.py,39
  tests/test_nlp2dsl_sdk.py,277
  tests/test_placeholder.py,12
  tests/test_tests.py,12
  tree.sh,2
  worker/__init__.py,6
  worker/config.py,28
  worker/logging_setup.py,101
  worker/tests/__init__.py,1
  worker/tests/conftest.py,46
  worker/tests/test_worker.py,173
  worker/worker.py,231
D:
  backend/app/__init__.py:
  backend/app/config.py:
    e: BackendSettings
    BackendSettings:
  backend/app/db/__init__.py:
    e: create_workflow_repo,WorkflowRepo
    WorkflowRepo: save_run(4),update_run_status(2),get_run(1),list_runs(2),count_runs(0)  # Abstrakcja persystencji workflow.
    create_workflow_repo()
  backend/app/db/memory.py:
    e: MemoryWorkflowRepo
    MemoryWorkflowRepo: __init__(1),save_run(4),update_run_status(2),get_run(1),list_runs(2),count_runs(0)
  backend/app/db/postgres.py:
    e: Base,WorkflowRunModel,PostgresWorkflowRepo
    Base:
    WorkflowRunModel: to_dict(0)
    PostgresWorkflowRepo: __init__(1),_ensure_engine(0),_get_session_factory(0),_ensure_tables(0),save_run(4),update_run_status(2),get_run(1),list_runs(2),count_runs(0),close(0)
  backend/app/engine.py:
    e: _workflow_steps_payload,_persist_workflow_snapshot,_publish_workflow_event,_execute_workflow,_track_background_task,run_workflow,start_workflow
    _workflow_steps_payload(result)
    _persist_workflow_snapshot(req;result)
    _publish_workflow_event(workflow_id;event_type;status;message)
    _execute_workflow(req;workflow_id)
    _track_background_task(task)
    run_workflow(req)
    start_workflow(req)
  backend/app/logging_setup.py:
    e: get_request_id,setup_logging,JSONFormatter,RequestIDMiddleware
    JSONFormatter: __init__(1),format(1)  # Emit log records as single-line JSON objects.
    RequestIDMiddleware: __init__(2),dispatch(2)  # Generate or forward X-Request-ID for every HTTP request.
    get_request_id()
    setup_logging(service;level)
  backend/app/main.py:
    e: health
    health()
  backend/app/routers/__init__.py:
  backend/app/routers/chat.py:
    e: _proxy_chat_payload,chat_start,chat_message,chat_get_state
    _proxy_chat_payload(request;endpoint)
    chat_start(request)
    chat_message(request)
    chat_get_state(conversation_id)
  backend/app/routers/settings.py:
    e: actions_schema,action_schema,get_settings,get_settings_section,update_settings_section,set_setting,reset_settings
    actions_schema()
    action_schema(action)
    get_settings()
    get_settings_section(section)
    update_settings_section(section;body)
    set_setting(body)
    reset_settings(body)
  backend/app/routers/system.py:
    e: system_execute
    system_execute(body)
  backend/app/routers/workflow.py:
    e: _format_sse,_workflow_snapshot,orient_nlp,list_actions,run_workflow_endpoint,start_workflow_endpoint,get_history,get_workflow,stream_workflow,workflow_from_text
    _format_sse(event;data)
    _workflow_snapshot(run)
    orient_nlp(body)
    list_actions()
    run_workflow_endpoint(req)
    start_workflow_endpoint(req)
    get_history()
    get_workflow(workflow_id)
    stream_workflow(workflow_id;request)
    workflow_from_text(body)
  backend/app/schemas.py:
    e: StepStatus,Step,RunWorkflowRequest,StepResult,WorkflowResult,ActionInfo
    StepStatus:
    Step:  # Pojedynczy krok workflow — deklaratywny opis akcji.
    RunWorkflowRequest:  # Żądanie uruchomienia workflow — DSL biznesowy.
    StepResult:
    WorkflowResult:
    ActionInfo:  # Opis dostępnej akcji (do listowania w GUI / API).
  backend/app/workflow.py:
  backend/app/workflow_events.py:
    e: WorkflowEvent,WorkflowEventHub
    WorkflowEvent: is_terminal(0),to_dict(0)
    WorkflowEventHub: __init__(0),subscribe(1),unsubscribe(2),publish(1),subscriber_count(1)  # In-memory broadcaster dla workflow lifecycle events.
  backend/tests/__init__.py:
  backend/tests/conftest.py:
    e: client
    client()
  backend/tests/test_config.py:
    e: TestBackendSettingsDefaults,TestBackendSettingsEnvOverride,TestBackendSettingsIntegration
    TestBackendSettingsDefaults: test_worker_url_default(1),test_nlp_service_url_default(1),test_postgres_url_default_none(1),test_log_level_default(1)  # BackendSettings reads sane defaults when env vars are absent
    TestBackendSettingsEnvOverride: test_worker_url_from_env(1),test_postgres_url_from_env(1),test_log_level_from_env(1),test_extra_env_vars_ignored(1)  # BackendSettings picks up values from env vars.
    TestBackendSettingsIntegration: test_settings_singleton_importable(0),test_engine_uses_settings(0)  # BackendSettings singleton is importable and functional.
  backend/tests/test_logging.py:
    e: TestJSONFormatter,TestRequestIDMiddleware,TestSetupLogging
    TestJSONFormatter: test_format_produces_json(0),test_format_includes_exception(0),test_format_service_name(0)  # JSONFormatter emits valid JSON with expected fields.
    TestRequestIDMiddleware: test_app(0),test_response_has_request_id_header(1),test_client_request_id_is_forwarded(1),test_new_id_generated_without_header(1)  # RequestIDMiddleware adds X-Request-ID to responses.
    TestSetupLogging: test_setup_logging_installs_json_handler(0),test_setup_logging_respects_log_level(0)  # setup_logging() installs JSONFormatter on root logger.
  backend/tests/test_persistence.py:
    e: TestMemoryRepoCRUD,TestMemoryRepoListOrdering,TestMemoryRepoEviction,TestSerializationRoundtrip,TestWorkflowRepoFactory
    TestMemoryRepoCRUD: repo(0),test_save_and_get(1),test_get_nonexistent(1),test_update_status(1),test_update_nonexistent(1),test_count_empty(1),test_count_after_saves(1)  # Basic CRUD on MemoryWorkflowRepo.
    TestMemoryRepoListOrdering: populated_repo(0),test_list_default(1),test_list_with_limit(1),test_list_with_offset(1)  # list_runs returns items in reverse insertion order (newest f
    TestMemoryRepoEviction: test_eviction_oldest(0)  # MemoryWorkflowRepo enforces max_size.
    TestSerializationRoundtrip: test_steps_json_roundtrip(0)  # Data saved to repo preserves all fields through roundtrip.
    TestWorkflowRepoFactory: test_factory_returns_memory_without_postgres(1),test_factory_returns_postgres_with_url(1)  # create_workflow_repo() factory behavior.
  backend/tests/test_workflow_api.py:
    e: _mock_worker_response,TestHealthEndpoint,TestWorkflowActions,TestRunWorkflow,TestWorkflowHistory,TestFromText
    TestHealthEndpoint: test_health_endpoint(1)  # Backend health check.
    TestWorkflowActions: test_workflow_actions(1),test_workflow_actions_contains_invoice(1)  # GET /workflow/actions endpoint.
    TestRunWorkflow: test_run_workflow(1),test_run_workflow_step_failure(1),test_start_workflow(1),test_stream_workflow(1)  # POST /workflow/run endpoint.
    TestWorkflowHistory: test_workflow_history(1)  # GET /workflow/history endpoint.
    TestFromText: test_from_text_complete(1),test_from_text_incomplete(1),test_from_text_empty(1)  # POST /workflow/from-text endpoint.
    _mock_worker_response(status_code;json_data)
  examples/01-invoice/main.py:
  examples/01-invoice/scenario.py:
    e: run
    run(client)
  examples/02-email/main.py:
  examples/02-email/scenario.py:
    e: run
    run(client)
  examples/03-report-and-notify/main.py:
  examples/03-report-and-notify/scenario.py:
    e: run
    run(client)
  examples/04-scheduled-report/main.py:
  examples/04-scheduled-report/scenario.py:
    e: run
    run(client)
  examples/05-conversation-flow/main.py:
  examples/05-conversation-flow/scenario.py:
    e: run_demo,run_interactive,run
    run_demo(client)
    run_interactive(client)
    run(client)
  examples/06-interactive-chat/main.py:
  examples/06-interactive-chat/scenario.py:
    e: run_demo,run_interactive,run
    run_demo(client)
    run_interactive(client)
    run(client)
  examples/07-email-conversation/main.py:
  examples/07-email-conversation/scenario.py:
    e: run
    run(client)
  examples/08-multi-object-benchmark/benchmark_queries.py:
    e: BenchmarkQuery
    BenchmarkQuery:
  examples/08-multi-object-benchmark/main.py:
  examples/08-multi-object-benchmark/scenario.py:
    e: _extract_actions,_evaluate,run_benchmark,run
    _extract_actions(result)
    _evaluate(query;result)
    run_benchmark(client)
    run(client)
  examples/09-execution-smoke/main.py:
  examples/09-execution-smoke/scenario.py:
    e: run
    run(client)
  examples/10-llm-benchmark/main.py:
  examples/10-llm-benchmark/scenario.py:
    e: run
    run(client)
  examples/11-notify-quality/main.py:
  examples/11-notify-quality/scenario.py:
    e: run
    run(client)
  examples/12-ir-show/main.py:
  examples/12-ir-show/scenario.py:
    e: _run_show,run
    _run_show(query)
    run(client)
  examples/bootstrap.py:
    e: bootstrap
    bootstrap(example_dir)
  examples/code_generation_examples.py:
    e: main
    main()
  nlp-service/app/__init__.py:
  nlp-service/app/access/__init__.py:
  nlp-service/app/access/bootstrap.py:
  nlp-service/app/access/config.py:
  nlp-service/app/access/native.py:
  nlp-service/app/access/policy.py:
  nlp-service/app/access/uri_match.py:
  nlp-service/app/audio_parser.py:
    e: stt_audio,stt_file,is_stt_available,StreamingSTT
    StreamingSTT: __init__(1),start(0),send_audio(1),get_transcript(0),stop(0)  # Real-time streaming STT via Deepgram WebSocket.
    stt_audio(audio_bytes;language)
    stt_file(file_path;language)
    is_stt_available()
  nlp-service/app/code_generator.py:
    e: CodeGenerator
    CodeGenerator: __init__(0),_get_api_key(0),_build_prompt(3),generate_code(4),_extract_class_name(1),_split_code_and_tests(2),get_supported_languages(0),get_language_info(1)  # Generates code in multiple programming languages using LLM.
  nlp-service/app/config.py:
    e: NLPServiceSettings
    NLPServiceSettings:
  nlp-service/app/conversation/__init__.py:
  nlp-service/app/conversation/merge.py:
    e: merge_into_state
    merge_into_state(state;nlp)
  nlp-service/app/conversation/orchestrator.py:
    e: start_conversation,continue_conversation,get_conversation,_attach_routing,_process_message
    start_conversation(text)
    continue_conversation(conversation_id;text)
    get_conversation(conversation_id)
    _attach_routing(resp;decision)
    _process_message(state;text)
  nlp-service/app/conversation/responses.py:
    e: deny_message,_execute_keyword_in_text,_is_execute_or_continue,check_execute_keyword,handle_unknown_intent,handle_system_action,build_and_check_dsl,build_incomplete_response,_nlp_from_state,format_system_result,_format_system_status,_format_settings_get,_format_settings_set,_format_settings_reset,_format_file_read,_format_file_write,_format_file_list,_format_registry_list,_format_registry_update
    deny_message(decision)
    _execute_keyword_in_text(text_lower;keyword)
    _is_execute_or_continue(text)
    check_execute_keyword(state;text)
    handle_unknown_intent(state)
    handle_system_action(state)
    build_and_check_dsl(state)
    build_incomplete_response(state)
    _nlp_from_state(state)
    format_system_result(intent;result)
    _format_system_status(inner)
    _format_settings_get(inner)
    _format_settings_set(inner)
    _format_settings_reset(inner)
    _format_file_read(inner)
    _format_file_write(inner)
    _format_file_list(inner)
    _format_registry_list(inner)
    _format_registry_update(inner)
  nlp-service/app/dsl/__init__.py:
  nlp-service/app/dsl/forms.py:
    e: get_action_form
    get_action_form(action)
  nlp-service/app/dsl/mapper.py:
    e: map_to_dsl,_resolve_actions,_build_config,_auto_notify_message,_get_field_mapping,_make_name,_build_prompt
    map_to_dsl(nlp)
    _resolve_actions(intent)
    _build_config(action;entities)
    _auto_notify_message(config;entities_dict)
    _get_field_mapping(action)
    _make_name(intent;actions)
    _build_prompt(missing)
  nlp-service/app/dsl/pipeline.py:
    e: map_to_dsl_with_enrichment
    map_to_dsl_with_enrichment(nlp)
  nlp-service/app/execution/__init__.py:
  nlp-service/app/execution/delegate.py:
    e: is_delegated_to_mullm,execution_backend_for_intent,mullm_action_names,delegate_payload
    is_delegated_to_mullm(intent)
    execution_backend_for_intent(intent)
    mullm_action_names()
    delegate_payload(action;config)
  nlp-service/app/execution/system.py:
    e: _validate_file_path,_is_read_only,execute_system_action,_exec_settings_get,_exec_settings_set,_exec_settings_reset,_exec_file_read,_exec_file_write,_exec_file_list,_exec_registry_list,_exec_registry_add,_exec_registry_edit,_exec_status
    _validate_file_path(file_path)
    _is_read_only(file_path)
    execute_system_action(action;config)
    _exec_settings_get(config)
    _exec_settings_set(config)
    _exec_settings_reset(config)
    _exec_file_read(config)
    _exec_file_write(config)
    _exec_file_list(config)
    _exec_registry_list(config)
    _exec_registry_add(config)
    _exec_registry_edit(config)
    _exec_status(config)
  nlp-service/app/governance/__init__.py:
  nlp-service/app/governance/bootstrap.py:
    e: _actions_from_yaml_areas,apply_yaml_actions,bootstrap_registry
    _actions_from_yaml_areas()
    apply_yaml_actions(registry)
    bootstrap_registry(registry)
  nlp-service/app/governance/config.py:
    e: _search_paths,_load_yaml_file,_merge_dict,load_access_config,_load_merged_config,_build_access_config,_enabled_integrations,_default_agent,_allowed_uri_schemes,get_access_config,reload_access_config,AccessConfig
    AccessConfig: action_to_area(0),area_by_id(1)
    _search_paths()
    _load_yaml_file(path)
    _merge_dict(base;overlay)
    load_access_config()
    _load_merged_config()
    _build_access_config(merged;loaded_path)
    _enabled_integrations(merged)
    _default_agent(settings;access_control)
    _allowed_uri_schemes(access_control)
    get_access_config()
    reload_access_config()
  nlp-service/app/governance/policy.py:
    e: get_agent_id,_grant_matches,_grant_action_matches,_grant_target_matches,_area_selector_match,_uri_selector_match,authorize_action,_action_context,_scheme_decision,_effect_decision,_unknown_agent_decision,_matched_effect,_decision,AccessDecision,_ActionContext
    AccessDecision: to_dict(0)
    _ActionContext:
    get_agent_id(header_agent)
    _grant_matches(grant)
    _grant_action_matches(grant;permission_action)
    _grant_target_matches(grant)
    _area_selector_match(area_key;resource_area)
    _uri_selector_match(uri_pattern;uri)
    authorize_action(agent_id;action_name)
    _action_context(meta)
    _scheme_decision(context)
    _effect_decision(matched_effect;agent_id;action_name;context)
    _unknown_agent_decision(agent_id;action_name)
    _matched_effect(grants)
    _decision(allowed;effect;reason;agent_id;action_name;resource_area;uri)
  nlp-service/app/governance/uri_match.py:
    e: normalize_uri,uri_matches,scheme_allowed
    normalize_uri(uri)
    uri_matches(pattern;uri)
    scheme_allowed(uri;allowed_schemes)
  nlp-service/app/logging_setup.py:
    e: get_request_id,setup_logging,JSONFormatter,RequestIDMiddleware
    JSONFormatter: __init__(1),format(1)  # Emit log records as single-line JSON objects.
    RequestIDMiddleware: __init__(2),dispatch(2)  # Generate or forward X-Request-ID for every HTTP request.
    get_request_id()
    setup_logging(service;level)
  nlp-service/app/main.py:
    e: orient_text,parse_text,text_to_dsl,access_config,access_check,access_reload,list_actions,health,chat_start,chat_message,chat_state,actions_schema,action_schema,get_settings,get_settings_section,update_settings_section,set_setting,reset_settings,system_execute,generate_code,get_supported_languages,_run_parser,websocket_chat,chat_ui
    orient_text(req)
    parse_text(req)
    text_to_dsl(req)
    access_config()
    access_check(agent_id;action;resource_area;uri;permission_action)
    access_reload()
    list_actions()
    health()
    chat_start(text;audio)
    chat_message(conversation_id;text;audio)
    chat_state(conversation_id)
    actions_schema()
    action_schema(action)
    get_settings()
    get_settings_section(section)
    update_settings_section(section;body)
    set_setting(body)
    reset_settings(body)
    system_execute(body)
    generate_code(body)
    get_supported_languages()
    _run_parser(req)
    websocket_chat(websocket;conversation_id)
    chat_ui()
  nlp-service/app/mapper.py:
  nlp-service/app/orchestrator.py:
  nlp-service/app/parser_enrich.py:
  nlp-service/app/parser_llm.py:
  nlp-service/app/parser_rules.py:
  nlp-service/app/parsing/__init__.py:
  nlp-service/app/parsing/facade.py:
  nlp-service/app/registry.py:
    e: get_action_by_alias,get_trigger,get_required_fields,get_defaults,get_quality_required_fields
    get_action_by_alias(text)
    get_trigger(text)
    get_required_fields(action)
    get_defaults(action)
    get_quality_required_fields(action)
  nlp-service/app/routing/__init__.py:
  nlp-service/app/routing/intent.py:
    e: IntentDecision
    IntentDecision: to_dict(0),to_nlp_result(1)  # Wynik `resolve_intent` — spójny kontrakt dla orchestratora i
  nlp-service/app/routing/native.py:
    e: _match_route,_patterns_match,_pattern_matches,_regex_pattern_matches,_keywords_pattern_matches,_substring_pattern_matches,_aliases_match,resolve_native_intent,_resolve_configured_route,_route_decision,_resolve_action_alias,_best_action_alias,_best_alias_for_action
    _match_route(text;route)
    _patterns_match(text_lower;patterns)
    _pattern_matches(text_lower;pattern)
    _regex_pattern_matches(text_lower;pattern)
    _keywords_pattern_matches(text_lower;pattern)
    _substring_pattern_matches(text_lower;pattern)
    _aliases_match(text_lower;aliases)
    resolve_native_intent(text)
    _resolve_configured_route(text;routes;action_areas)
    _route_decision(action;route;action_areas)
    _resolve_action_alias(text;registry)
    _best_action_alias(text_lower;registry)
    _best_alias_for_action(text_lower;action_name;meta;current)
  nlp-service/app/routing/observability.py:
    e: record_intent_decision,routing_metrics_snapshot,reset_routing_metrics
    record_intent_decision(decision)
    routing_metrics_snapshot()
    reset_routing_metrics()
  nlp-service/app/routing/orientation.py:
    e: _has_registry_hint,_has_host_hint,_is_file_list_query,_file_list_scope,_host_list_root,_normalize_orient_path,_resolve_project_host_path,_resolve_list_path_remainder,_resolve_file_list_host_command,orient_query,OrientationResult
    OrientationResult: to_dict(0)
    _has_registry_hint(text)
    _has_host_hint(text)
    _is_file_list_query(text)
    _file_list_scope(text)
    _host_list_root()
    _normalize_orient_path(path;root)
    _resolve_project_host_path(project_name;root)
    _resolve_list_path_remainder(remainder;root)
    _resolve_file_list_host_command(text)
    orient_query(text)
  nlp-service/app/routing/parser/__init__.py:
  nlp-service/app/routing/parser/enrich.py:
    e: is_enrich_enabled,get_enrichable_missing,can_enrich_missing,enrich_entities
    is_enrich_enabled()
    get_enrichable_missing(missing_fields)
    can_enrich_missing(missing_fields)
    enrich_entities(nlp;missing_fields)
  nlp-service/app/routing/parser/facade.py:
    e: parse_text
    parse_text(text;mode)
  nlp-service/app/routing/parser/llm.py:
    e: parse_llm,_detect_provider,_parse_json_response
    parse_llm(text)
    _detect_provider()
    _parse_json_response(raw)
  nlp-service/app/routing/parser/prompt_catalog.py:
    e: build_llm_system_prompt
    build_llm_system_prompt()
  nlp-service/app/routing/parser/resolve_mode.py:
    e: parse_with_mode
    parse_with_mode(text;mode)
  nlp-service/app/routing/parser/rules.py:
    e: parse_rules,_detect_actions,_apply_context_filters,_action_alias_scores,_alias_in_text,_longest_alias_match,_actions_by_score,_dominant_overlap_action,_action_category,_top_system_action_wins,_second_system_action_wins,_resolve_intent,_extract_entities,_extract_amount,_extract_email,_extract_body_content_prefix,_extract_email_subject_and_body,_extract_reminder_subject,_extract_report_type,_extract_format,_extract_notification_channels,_extract_notification_message,_extract_param_aliases,_extract_system_entities,_extract_file_path_entity,_extract_setting_path_entity,_extract_model_setting_entity,_extract_numeric_setting_value,_extract_mode_setting_entity,_extract_fallback_recipient,_set_entity
    parse_rules(text)
    _detect_actions(text_lower)
    _apply_context_filters(text_lower;scores)
    _action_alias_scores(text_lower)
    _alias_in_text(text_lower;alias_text)
    _longest_alias_match(text_lower;aliases)
    _actions_by_score(scores)
    _dominant_overlap_action(sorted_actions;scores)
    _action_category(action_name)
    _top_system_action_wins(top_category;second_category;top_score;second_score)
    _second_system_action_wins(top_category;second_category;top_score;second_score)
    _resolve_intent(actions)
    _extract_entities(text;text_lower)
    _extract_amount(entities;text)
    _extract_email(entities;text)
    _extract_body_content_prefix(entities;text)
    _extract_email_subject_and_body(entities;text)
    _extract_reminder_subject(entities;text)
    _extract_report_type(entities;text_lower)
    _extract_format(entities;text_lower)
    _extract_notification_channels(entities;text)
    _extract_notification_message(entities;text)
    _extract_param_aliases(entities;text_lower)
    _extract_system_entities(entities;text;text_lower)
    _extract_file_path_entity(entities;text)
    _extract_setting_path_entity(entities;text)
    _extract_model_setting_entity(entities;text_lower)
    _extract_numeric_setting_value(entities;text_lower)
    _extract_mode_setting_entity(entities;text_lower)
    _extract_fallback_recipient(entities;text_lower)
    _set_entity(entities;field;value)
  nlp-service/app/routing/resolve.py:
    e: _parser_source,_intent_from_native,_intent_from_nlp,_apply_auth,_intent_from_orientation,resolve_intent
    _parser_source(text)
    _intent_from_native(native)
    _intent_from_nlp(nlp;source)
    _apply_auth(decision;auth)
    _intent_from_orientation(text;orientation)
    resolve_intent(text)
  nlp-service/app/schemas.py:
    e: NLPIntent,NLPEntities,NLPResult,DSLStep,WorkflowDSL,DialogResponse,NLPRequest,OrientRequest,ConversationState,FieldSchema,ActionFormSchema,ConversationResponse
    NLPIntent:
    NLPEntities:
    NLPResult:
    DSLStep:
    WorkflowDSL:
    DialogResponse:
    NLPRequest:
    OrientRequest:
    ConversationState:  # Stan rozmowy — akumuluje dane między turami dialogu.
    FieldSchema:
    ActionFormSchema:
    ConversationResponse:
  nlp-service/app/settings.py:
    e: _coerce_type,LLMSettings,NLPSettings,WorkerSettings,FileAccessSettings,SystemSettings,SettingsManager
    LLMSettings:
    NLPSettings:
    WorkerSettings:
    FileAccessSettings:
    SystemSettings:  # Pełny model ustawień systemu.
    SettingsManager: __new__(1),settings(0),get(1),get_section(1),get_all(0),set(2),update_section(2),reset(1),_load(0),_save(0),describe(0)  # Runtime settings z persystencją do JSON.
    _coerce_type(value;target_type)
  nlp-service/app/store/__init__.py:
    e: ConversationStore
    ConversationStore: get(1),save(2),delete(1),count(0)  # Abstrakcja persystencji stanu konwersacji.
  nlp-service/app/store/factory.py:
    e: get_conversation_store
    get_conversation_store()
  nlp-service/app/store/memory.py:
    e: MemoryConversationStore
    MemoryConversationStore: __init__(0),get(1),save(2),delete(1),count(0)
  nlp-service/app/store/redis_store.py:
    e: RedisConversationStore
    RedisConversationStore: __init__(2),_key(1),get(1),save(2),delete(1),count(0),close(0)
  nlp-service/app/system_executor.py:
  nlp-service/integrations/__init__.py:
  nlp-service/integrations/loader.py:
    e: _integration_names,load_integration_registries,apply_integrations
    _integration_names()
    load_integration_registries()
    apply_integrations(registry)
  nlp-service/integrations/mullm/__init__.py:
  nlp-service/integrations/mullm/registry.py:
  nlp-service/tests/__init__.py:
  nlp-service/tests/conftest.py:
    e: sample_texts,expected_intents,sample_entities,mock_conversation_store
    sample_texts()
    expected_intents()
    sample_entities()
    mock_conversation_store()
  nlp-service/tests/test_access.py:
    e: _point_config,test_config_loads_areas,test_uri_match_mullm,test_files_agent_can_list,test_mail_agent_denied_mullm_execute,test_native_lista_plikow_registry,test_registry_has_yaml_action
    _point_config(monkeypatch)
    test_config_loads_areas()
    test_uri_match_mullm()
    test_files_agent_can_list()
    test_mail_agent_denied_mullm_execute()
    test_native_lista_plikow_registry()
    test_registry_has_yaml_action()
  nlp-service/tests/test_enrich.py:
    e: _enable_enrich,_FakeMessage,_FakeChoice,_FakeResponse,TestEnrichHelpers,TestEnrichEntities,TestEnrichPipeline
    _FakeMessage: __init__(1)
    _FakeChoice: __init__(1)
    _FakeResponse: __init__(1)
    TestEnrichHelpers: test_is_enrich_enabled(1),test_get_enrichable_missing_body_only(0),test_get_enrichable_missing_ignores_required(0),test_can_enrich_only_quality_fields(1)
    TestEnrichEntities: test_enrich_fills_email_body(2),test_enrich_disabled_returns_none(1),test_enrich_fills_notify_message(2)
    TestEnrichPipeline: test_pipeline_completes_after_enrich(2)
    _enable_enrich(monkeypatch)
  nlp-service/tests/test_execution_delegate.py:
    e: test_mullm_shell_delegated,test_invoice_worker_backend,test_delegate_payload_shape
    test_mullm_shell_delegated()
    test_invoice_worker_backend()
    test_delegate_payload_shape()
  nlp-service/tests/test_mapper.py:
    e: TestMapCompleteDSL,TestMapIncomplete,TestMapComposite,TestMapUnknown,TestMapDefaults,TestMapTrigger,TestMapSystemAction,TestMapAllBusinessActions,TestResolveActions
    TestMapCompleteDSL: test_map_complete_invoice(0),test_map_complete_email(0),test_map_incomplete_email_missing_body(0)  # Cases where all required fields are present → complete DSL.
    TestMapIncomplete: test_map_incomplete_invoice(0),test_map_composite_invoice_email_separate_recipients(0)  # Cases where required fields are missing → DialogResponse wit
    TestMapComposite: test_map_composite_report_email(0)  # Composite intent mapping (multi-step workflows).
    TestMapUnknown: test_map_unknown_intent(0),test_map_nonexistent_intent(0)  # Unknown intent → error response.
    TestMapDefaults: test_map_with_defaults(0)  # Optional fields receive default values from registry.
    TestMapTrigger: test_map_trigger_propagation(0)  # Trigger extracted from raw_text propagates to DSL.
    TestMapSystemAction: test_map_system_action_settings(0)  # System intents should not map to DSL (no steps for system ac
    TestMapAllBusinessActions: test_map_all_business_actions(1)  # Ensure mapper handles all registered business actions.
    TestResolveActions: test_resolve_direct_action(0),test_resolve_composite_intent(0),test_resolve_dynamic_composite(0),test_resolve_unknown(0)  # _resolve_actions helper tests.
  nlp-service/tests/test_orchestrator.py:
    e: _patch_store,TestStartConversation,TestExecuteKeywordMatching,TestContinueConversation,TestSystemCommands,TestGetConversation,TestGetActionForm,TestMergeIntoState
    TestStartConversation: test_start_conversation_complete(0),test_start_conversation_incomplete(0),test_start_conversation_unknown(0)  # Starting a new conversation from initial user text.
    TestExecuteKeywordMatching: test_go_not_matched_inside_zgodnie(0)
    TestContinueConversation: test_continue_conversation(0),test_continue_conversation_lazy_create(0),test_continue_conversation_email_body(0)  # Multi-turn dialog: providing missing data in follow-up messa
    TestSystemCommands: test_system_command_status(0),test_system_command_settings(0),test_format_system_file_list(0),test_format_system_failed_result(0)  # System actions executed directly (no DSL generation).
    TestGetConversation: test_get_conversation_exists(0),test_get_conversation_not_found(0)  # Retrieving stored conversation state.
    TestGetActionForm: test_action_form_send_invoice(0),test_action_form_nonexistent(0)  # Schema-driven UI form generation.
    TestMergeIntoState: test_merge_updates_intent(0),test_merge_preserves_existing(0)  # Internal entity merging logic.
    _patch_store(monkeypatch)
  nlp-service/tests/test_orientation.py:
    e: TestOrientQuery,TestResolveIntentOrientation
    TestOrientQuery: test_lista_plikow_usera_host_default_mullm(0),test_lista_plikow_github_path_hint(0),test_lista_plikow_systemu_root_fs(0),test_lista_plikow_linux_host_home(0),test_lista_plikow_root_slash(0),test_lista_plikow_projektu_nlp2cmd(0),test_lista_plikow_w_github_multi_segment(0),test_lista_plikow_projektu_only(0),test_lista_plikow_usera_registry(0),test_pokaz_pliki_local_connector(0),test_run_prefix_shell(0),test_disk_space_shell_nl(0),test_invoice_workflow_hint(0)
    TestResolveIntentOrientation: test_lista_plikow_usera_short_circuit_shell(0),test_registry_list_short_circuit_mullm_files(0)
  nlp-service/tests/test_parser_rules.py:
    e: TestParseInvoice,TestParseEmail,TestParseNotifyQuality,TestParseReport,TestParseComposite,TestParseSystem,TestParseUnknown,TestAmountExtraction,TestTriggerDetection,TestResultStructure
    TestParseInvoice: test_parse_invoice_simple(0),test_parse_invoice_missing_data(0),test_parse_invoice_eur(0),test_parse_invoice_usd(0)  # Invoice intent detection and entity extraction.
    TestParseEmail: test_parse_email(0),test_parse_email_english(0),test_parse_email_reminder(0),test_parse_email_with_subject(0),test_parse_email_colon_body(0),test_parse_body_content_prefix(0),test_parse_body_content_prefix_long_form(0),test_parse_email_offer(0),test_parse_slack_with_message(0),test_parse_slack_about_message(0)  # Email intent detection.
    TestParseNotifyQuality: test_notify_channel_only_maps_incomplete_without_message(0)
    TestParseReport: test_parse_report_weekly(0),test_parse_report_hr_xlsx_no_false_system(0),test_parse_report_finance_csv(0)  # Report intent and entity extraction.
    TestParseComposite: test_parse_composite_invoice_notify(0),test_parse_composite_full_flow(0)  # Multi-action (composite) intent detection.
    TestParseSystem: test_parse_system_settings(0),test_parse_system_file_list(0),test_parse_system_status(0),test_parse_system_help(0),test_parse_system_set_model(0),test_parse_system_set_mode(0)  # System intent detection (settings, files, status).
    TestParseUnknown: test_parse_unknown(0)  # Unknown input handling.
    TestAmountExtraction: test_parse_amount_extraction(3)  # Currency and amount parsing across formats.
    TestTriggerDetection: test_parse_trigger_detection(2)  # Schedule trigger extraction from text.
    TestResultStructure: test_result_is_nlp_result(0),test_raw_text_preserved(0)  # NLPResult output structure validation.
  nlp-service/tests/test_registry.py:
    e: TestRegistryStructure,TestAliasResolution,TestTriggerDetection,TestHelperFunctions,TestCategories,TestCompositeIntents
    TestRegistryStructure: test_registry_entry_has_required_keys(1)  # Validate registry entries have required keys.
    TestAliasResolution: test_alias_invoice_pl(0),test_alias_email_en(0),test_alias_report(0),test_alias_slack(0),test_alias_unknown(0),test_alias_best_match(0)  # get_action_by_alias finds best match.
    TestTriggerDetection: test_trigger_daily(0),test_trigger_weekly(0),test_trigger_monthly(0),test_trigger_manual_default(0)  # get_trigger extracts schedule from text.
    TestHelperFunctions: test_get_required_fields_invoice(0),test_get_required_fields_unknown(0),test_get_defaults_invoice(0),test_get_defaults_unknown(0)  # get_required_fields, get_defaults.
    TestCategories: test_system_actions_nonempty(0),test_business_actions_nonempty(0),test_no_overlap(0),test_union_is_complete(0),test_mullm_actions_loaded(0)  # System vs business action sets.
    TestCompositeIntents: test_composite_actions_exist(1)  # COMPOSITE_INTENTS structure validation.
  nlp-service/tests/test_routing_observability.py:
    e: _reset_metrics,test_record_increments_rules_hit,test_resolve_intent_updates_metrics
    _reset_metrics()
    test_record_increments_rules_hit()
    test_resolve_intent_updates_metrics()
  nlp-service/tests/test_routing_resolve.py:
    e: TestParserSource,TestResolveIntent,TestOrchestratorRoutingField
    TestParserSource: test_rules_mode(1)
    TestResolveIntent: test_invoice_rules_path(0),test_unknown_intent(0),test_native_file_list_route(0),test_decision_serializable(0)
    TestOrchestratorRoutingField: test_start_conversation_includes_routing(1)
  nlp-service/tests/test_store.py:
    e: TestMemoryStoreCRUD,TestSerializationRoundtrip,TestStoreFactory,TestStoreIsolation
    TestMemoryStoreCRUD: store(0),test_save_and_get(1),test_get_nonexistent(1),test_save_overwrites(1),test_delete(1),test_delete_nonexistent(1),test_count_empty(1),test_count_after_saves(1),test_count_after_delete(1)  # Basic CRUD operations on MemoryConversationStore.
    TestSerializationRoundtrip: store(0),test_conversation_state_roundtrip(1),test_complex_entities_roundtrip(1)  # Store must preserve data through save→get cycle.
    TestStoreFactory: test_factory_returns_memory_without_redis(1),test_factory_singleton(1),test_factory_falls_back_on_bad_redis(1)  # get_conversation_store() factory behavior.
    TestStoreIsolation: test_separate_instances_isolated(0)  # Multiple store instances are isolated.
  nlp-service/tests/test_system_executor.py:
    e: _reset_settings,TestSettingsGet,TestSettingsSet,TestSettingsReset,TestFileList,TestRegistryList,TestRegistryAdd,TestStatus,TestRegistryEdit,TestFileRead,TestFileWrite,TestExecuteSystemAction,TestFilePathValidation,TestExecutorMapping
    TestSettingsGet: test_settings_get_all(0),test_settings_get_section(0),test_settings_get_default_is_all(0)  # _exec_settings_get handler.
    TestSettingsSet: test_settings_set_and_verify(0),test_settings_set_missing_path(0),test_settings_set_missing_value(0)  # _exec_settings_set handler.
    TestSettingsReset: test_settings_reset(0),test_settings_reset_section(0)  # _exec_settings_reset handler.
    TestFileList: test_file_list(2),test_file_list_nonexistent(0)  # _exec_file_list handler.
    TestRegistryList: test_registry_list(0),test_registry_list_business(0),test_registry_list_system(0)  # _exec_registry_list handler.
    TestRegistryAdd: test_registry_add(0),test_registry_add_missing_name(0),test_registry_add_duplicate(0)  # _exec_registry_add handler.
    TestStatus: test_status(0)  # _exec_status handler.
    TestRegistryEdit: test_registry_edit_description(0),test_registry_edit_nonexistent(0)  # _exec_registry_edit handler.
    TestFileRead: test_file_read_existing(2),test_file_read_nonexistent(2),test_file_read_no_path(0)  # _exec_file_read handler.
    TestFileWrite: test_file_write_new(2),test_file_write_append(2)  # _exec_file_write handler.
    TestExecuteSystemAction: test_execute_known_action(0),test_execute_unknown_action(0)  # Async dispatch function.
    TestFilePathValidation: test_validate_allowed_path(2),test_validate_disallowed_path(0),test_is_read_only(2)  # _validate_file_path and _is_read_only.
    TestExecutorMapping: test_all_system_actions_have_executor(0),test_executors_count(0)  # SYSTEM_EXECUTORS dict is complete.
    _reset_settings(monkeypatch)
  nlp2dsl_sdk/__init__.py:
  nlp2dsl_sdk/__main__.py:
    e: main
    main()
  nlp2dsl_sdk/artifacts.py:
    e: example_artifact_root,_slugify,_mask_secret,collect_environment,write_environment_doql,build_process_trace,_action_endpoint,_action_transport,write_query_artifacts,write_manifest,write_testql_commands,write_services_snapshot,_extract_actions,get_example_writer,ExampleArtifactWriter
    ExampleArtifactWriter: __init__(1),record(2),finalize(1)  # Accumulates query results and flushes .nlp2dsl/ on finalize(
    example_artifact_root(example_dir)
    _slugify(text)
    _mask_secret(value)
    collect_environment()
    write_environment_doql(artifact_root;example_name;env)
    build_process_trace(query;result)
    _action_endpoint(action)
    _action_transport(action)
    write_query_artifacts(artifact_root;query;result)
    write_manifest(artifact_root)
    write_testql_commands(artifact_root)
    write_services_snapshot(artifact_root;actions)
    _extract_actions(result)
    get_example_writer()
  nlp2dsl_sdk/cli.py:
    e: _analyze,_display,show,_client,_health,_run,_actions,_chat_start,_demo,main
    _analyze(query)
    _display(result)
    show(query)
    _client()
    _health()
    _run(query)
    _actions()
    _chat_start(text)
    _demo(name;list_demos)
    main(argv)
  nlp2dsl_sdk/client.py:
    e: workflow_step,NLP2DSLClient,ConversationFlow
    NLP2DSLClient: __init__(5),from_env(2),close(0),__enter__(0),__exit__(3),_request(3),_backend(2),_nlp_service(2),_worker(2),backend_health(0),nlp_service_health(0),worker_health(0),health(0),workflow_from_text(3),run_workflow(4),workflow_actions(0),workflow_action_schema(1),settings(0),settings_section(1),update_settings_section(2),set_setting(2),reset_settings(1),chat_start(2),chat_message(3),chat_state(1),nlp_chat_start(2),nlp_chat_message(3),nlp_chat_state(1),generate_code(4),supported_languages(0),worker_execute(3),worker_generate_code(5),send_invoice(5),send_email(5),generate_report(4),generate_report_and_notify(7),create_scheduled_report(7),notify_slack(4),crm_update(4),send_invoice_and_notify(7)  # Small reusable SDK for the NLP2DSL services.
    ConversationFlow: __init__(1),start(2),send_message(2),_handle_response(1),_handle_in_progress_response(2),_handle_ready_response(2),_handle_completed_response(2),_handle_error_response(1),run_demo(0),run_interactive(0)  # Convenience helper for the conversational workflow example.
    workflow_step(action)
  nlp2dsl_sdk/demos.py:
    e: _print_code_generation_preview,run_crm_update_demo,run_action_catalog_demo,run_automation_gallery_demo,run_code_generation_demo,_run_direct_code_generation,_get_supported_languages,_run_workflow_code_examples,_run_conversation_code_example,_run_worker_code_generation,list_available_demos,DemoSpec
    DemoSpec:  # Metadata for a runnable demo exposed by the package CLI.
    _print_code_generation_preview(result)
    run_crm_update_demo(client)
    run_action_catalog_demo(client)
    run_automation_gallery_demo(client)
    run_code_generation_demo(client)
    _run_direct_code_generation(client)
    _get_supported_languages(client)
    _run_workflow_code_examples(client)
    _run_conversation_code_example(client)
    _run_worker_code_generation(client)
    list_available_demos()
  nlp2dsl_sdk/encoding.py:
    e: utf8_auto_enabled,_explicit_utf8_locale,_apply_utf8_locale_env,_reconfigure_stdio,_set_utf8_locale,configure_utf8,_auto_configure_once,utf8_open
    utf8_auto_enabled()
    _explicit_utf8_locale()
    _apply_utf8_locale_env()
    _reconfigure_stdio()
    _set_utf8_locale()
    configure_utf8()
    _auto_configure_once()
    utf8_open(path;mode)
  nlp2dsl_sdk/example_loader.py:
    e: load_example_runner
    load_example_runner(example_dir)
  nlp2dsl_sdk/preview.py:
    e: print_json,print_workflow_preview,print_execution_result,workflow_http_error_result,preview_text_examples,execute_from_text,execute_text_examples,finalize_example_artifacts,ensure_services
    print_json(payload)
    print_workflow_preview(result)
    print_execution_result(result)
    workflow_http_error_result(exc)
    preview_text_examples(client;title;examples)
    execute_from_text(client;text)
    execute_text_examples(client;title;examples)
    finalize_example_artifacts(client)
    ensure_services(client)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/__init__.py:
  packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py:
    e: clarification_enforced,ensure_intent_clear,IntentClarificationRequired
    IntentClarificationRequired: __init__(1)  # Raised when IntentIR needs user clarification before plannin
    clarification_enforced()
    ensure_intent_clear(intent)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py:
    e: get_user_config_dir,_package_data_dir,_nlp2cmd_data_dir,find_data_files
    get_user_config_dir()
    _package_data_dir()
    _nlp2cmd_data_dir()
    find_data_files()
  packages/nlp2cmd-intent/src/nlp2cmd_intent/domain_mapping.py:
    e: domain_to_target_kind,intent_to_execution_risk
    domain_to_target_kind(domain)
    intent_to_execution_risk(intent)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py:
    e: default_intent_detector,PassthroughEntityExtractor,KeywordIntentAdapter,IntentPipeline
    PassthroughEntityExtractor: extract(1)
    KeywordIntentAdapter: __init__(1),detect(1)  # Wrap KeywordIntentDetector to satisfy IntentDetector protoco
    IntentPipeline: __init__(0),run(1)  # normalize → entities → intent.
    default_intent_detector()
  packages/nlp2cmd-intent/src/nlp2cmd_intent/input.py:
    e: analyze_query
    analyze_query(query)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/__init__.py:
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py:
    e: _get_query_normalizer,_get_polish_support,_get_fuzzy_schema_matcher,_get_ml_classifier,_get_semantic_matcher,_get_spacy_model,_normalize_url,DetectionResult,KeywordIntentDetector
    DetectionResult: __post_init__(0)  # Result of intent detection.
    KeywordIntentDetector: __init__(3),add_pattern(3),detect(1),detect_intent_ir(1),detect_all(1),_match_keyword(2),_fast_path_detection(2),_fuzzy_detection(1),_ml_detection(1),_semantic_detection(1),_keyword_detection(2),_calculate_keyword_confidence(2),_tokenize_text(1),_keyword_matches(3)  # Rule-based intent detection using keyword matching.
    _get_query_normalizer()
    _get_polish_support()
    _get_fuzzy_schema_matcher()
    _get_ml_classifier()
    _get_semantic_matcher()
    _get_spacy_model()
    _normalize_url(raw)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py:
    e: _find_data_files,_normalize_polish_text,_dedupe_case_insensitive,KeywordPatterns
    KeywordPatterns: __init__(1),_load_patterns_from_json(1),_load_detector_config_from_json(0),get_domain_patterns(1),get_intent_patterns(2),has_domain(1),has_intent(2),list_domains(0),list_intents(1),add_pattern(3),get_domain_boosters(1),get_priority_intents(1)  # Manages keyword patterns for intent detection.
    _find_data_files()
    _normalize_polish_text(text)
    _dedupe_case_insensitive(items)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/nlp2cmd_convert.py:
    e: detection_to_intent_ir
    detection_to_intent_ir(result)
  packages/nlp2cmd-intent/src/nlp2cmd_intent/normalize.py:
    e: QueryNormalizer
    QueryNormalizer: normalize(1)  # Lightweight normalizer; full Polish support migrates from nl
  packages/nlp2cmd-intent/src/nlp2cmd_intent/protocols.py:
    e: IntentDetector,EntityExtractor
    IntentDetector: detect(1)
    EntityExtractor: extract(1)
  packages/nlp2cmd-intent/tests/test_analyze_query.py:
    e: test_analyze_query_find_files
    test_analyze_query_find_files()
  packages/nlp2cmd-intent/tests/test_clarification.py:
    e: test_ensure_intent_clear_blocks_low_confidence,test_ensure_intent_clear_allows_confident_intent,test_analyze_query_enforces_clarification_with_env,test_analyze_query_allows_ambiguous_without_env
    test_ensure_intent_clear_blocks_low_confidence()
    test_ensure_intent_clear_allows_confident_intent()
    test_analyze_query_enforces_clarification_with_env(monkeypatch)
    test_analyze_query_allows_ambiguous_without_env(monkeypatch)
  packages/nlp2cmd-intent/tests/test_intent_pipeline.py:
    e: test_file_search_intent_with_keyword_detector
    test_file_search_intent_with_keyword_detector()
  packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py:
    e: test_detection_to_intent_ir_shell_find,test_detection_to_intent_ir_browser_navigate,FakeDetection
    FakeDetection:
    test_detection_to_intent_ir_shell_find()
    test_detection_to_intent_ir_browser_navigate()
  packages/nlp2cmd-planner/src/nlp2cmd_planner/__init__.py:
  packages/nlp2cmd-planner/src/nlp2cmd_planner/pipeline.py:
    e: PlanningPipeline
    PlanningPipeline: __init__(0),run(1)
  packages/nlp2cmd-planner/src/nlp2cmd_planner/router.py:
    e: UnsupportedIntentError,PlanRouter
    UnsupportedIntentError: __init__(1)  # No planning strategy supports the given intent.
    PlanRouter: __init__(1),select(1)
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/__init__.py:
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rest_workflow.py:
    e: RestWorkflowPlanStrategy
    RestWorkflowPlanStrategy: supports(1),plan(1)
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rule_shell.py:
    e: _parse_file_search,RuleShellPlanStrategy
    RuleShellPlanStrategy: supports(1),plan(1)
    _parse_file_search(intent)
  packages/nlp2cmd-planner/src/nlp2cmd_planner/strategy.py:
    e: PlanStrategy
    PlanStrategy: supports(1),plan(1)
  packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py:
    e: workflow_backend_enabled,workflow_backend_url,workflow_run_path,fetch_workflow_from_text
    workflow_backend_enabled()
    workflow_backend_url()
    workflow_run_path()
    fetch_workflow_from_text(query)
  packages/nlp2cmd-planner/tests/test_planning_pipeline.py:
    e: test_planning_pipeline_shell_find,test_planning_pipeline_shell_find_with_path,test_rule_shell_supports_find_intent,test_parse_file_search_from_entities,test_unsupported_intent_raises
    test_planning_pipeline_shell_find()
    test_planning_pipeline_shell_find_with_path()
    test_rule_shell_supports_find_intent()
    test_parse_file_search_from_entities()
    test_unsupported_intent_raises()
  packages/nlp2cmd-planner/tests/test_rest_workflow.py:
    e: _intent,test_supports_when_workflow_enabled,test_supports_disabled_without_env,test_plan_builds_rest_workflow_step,test_plan_raises_on_incomplete_workflow,test_router_prefers_shell_over_rest
    _intent()
    test_supports_when_workflow_enabled(monkeypatch)
    test_supports_disabled_without_env(monkeypatch)
    test_plan_builds_rest_workflow_step(monkeypatch)
    test_plan_raises_on_incomplete_workflow(monkeypatch)
    test_router_prefers_shell_over_rest(monkeypatch)
  packages/nlp2cmd-planner/tests/test_rest_workflow_propact.py:
    e: test_rest_workflow_renders_propact_markdown
    test_rest_workflow_renders_propact_markdown(monkeypatch)
  packages/nlp2cmd-propact/src/nlp2cmd_propact/__init__.py:
  packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py:
    e: _shell_block,_rest_block,_format_json_body,_mcp_block,_ws_block,_delegate_block,step_to_propact_block,plan_to_propact_markdown
    _shell_block(dsl)
    _rest_block(method;endpoint;body)
    _format_json_body(value)
    _mcp_block(step)
    _ws_block(step)
    _delegate_block(step)
    step_to_propact_block(step)
    plan_to_propact_markdown(plan)
  packages/nlp2cmd-propact/src/nlp2cmd_propact/cli.py:
    e: main
    main(argv)
  packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py:
    e: execution_route,_single_step_plan,HybridPlanExecutor
    HybridPlanExecutor: __init__(0),run(1),_run_propact_step(2),_run_nlp2cmd_step(2)  # Route plan steps to Propact or nlp2cmd based on target_kind.
    execution_route(step)
    _single_step_plan(plan;step)
  packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py:
    e: _propact_fallback_mode,_resolve_propact_bin,_propact_available,_is_shell_only,_requires_propact,_shell_command,_run_shell_steps,RunResult,PropactRunner
    RunResult:
    PropactRunner: __init__(0),render(1),run(1),_run_via_propact(2)  # Run ExecutionPlanIR through Propact CLI when available.
    _propact_fallback_mode()
    _resolve_propact_bin(propact_bin)
    _propact_available(propact_bin)
    _is_shell_only(plan)
    _requires_propact(plan)
    _shell_command(step_dsl;step_params)
    _run_shell_steps(plan)
  packages/nlp2cmd-propact/tests/test_adapter.py:
    e: test_shell_plan_to_markdown,test_rest_block_with_json_body,test_mcp_block_from_tool_params,test_mcp_block_from_dsl,test_ws_block_from_url_and_message,test_delegate_block_for_browser,test_delegate_block_for_sql,test_mixed_plan_renders_all_block_types
    test_shell_plan_to_markdown()
    test_rest_block_with_json_body()
    test_mcp_block_from_tool_params()
    test_mcp_block_from_dsl()
    test_ws_block_from_url_and_message()
    test_delegate_block_for_browser()
    test_delegate_block_for_sql()
    test_mixed_plan_renders_all_block_types()
  packages/nlp2cmd-propact/tests/test_executor.py:
    e: _shell_plan,_browser_plan,test_execution_route,test_hybrid_dry_run_includes_routes,test_hybrid_routes_shell_to_propact,test_hybrid_routes_browser_to_nlp2cmd,test_hybrid_stops_on_first_failure
    _shell_plan()
    _browser_plan()
    test_execution_route()
    test_hybrid_dry_run_includes_routes()
    test_hybrid_routes_shell_to_propact(mock_propact)
    test_hybrid_routes_browser_to_nlp2cmd(mock_nlp2cmd)
    test_hybrid_stops_on_first_failure(mock_propact)
  packages/nlp2cmd-propact/tests/test_runner.py:
    e: _shell_plan,test_run_dry_run_returns_markdown_only,test_run_executes_propact_without_dry_run,test_shell_fallback_when_propact_missing,test_rest_plan_fails_without_propact,test_shell_fallback_disabled_returns_error,test_shell_fallback_propagates_nonzero_exit,test_empty_plan_fails,test_propact_bin_env_override
    _shell_plan(dsl)
    test_run_dry_run_returns_markdown_only()
    test_run_executes_propact_without_dry_run(mock_available;mock_run)
    test_shell_fallback_when_propact_missing(mock_available;mock_run)
    test_rest_plan_fails_without_propact(mock_available)
    test_shell_fallback_disabled_returns_error(mock_available;monkeypatch)
    test_shell_fallback_propagates_nonzero_exit()
    test_empty_plan_fails()
    test_propact_bin_env_override(mock_available;mock_run;monkeypatch)
  packages/nlp2dsl-show/src/nlp2dsl_show/__init__.py:
  packages/nlp2dsl-show/src/nlp2dsl_show/cli.py:
    e: _serialize,main,_attach_contract_check
    _serialize(data;fmt)
    main(argv)
    _attach_contract_check(payload)
  packages/nlp2dsl-show/src/nlp2dsl_show/encoding.py:
  packages/nlp2dsl-show/tests/test_cli.py:
    e: test_build_query_structure_intent_only,test_build_query_structure_with_plan,test_cli_show_json,test_cli_show_rejects_ambiguous_query_when_enforced
    test_build_query_structure_intent_only()
    test_build_query_structure_with_plan()
    test_cli_show_json()
    test_cli_show_rejects_ambiguous_query_when_enforced()
  packages/pact-ir/src/pact_ir/__init__.py:
  packages/pact-ir/src/pact_ir/execution_plan.py:
    e: PlanStep,ExecutionPlanIR
    PlanStep:
    ExecutionPlanIR: from_intent(2),primary_target_kind(0),step_count(0)  # Standardized execution plan (nlp2cmd.execution_plan_ir.v1).
  packages/pact-ir/src/pact_ir/intent.py:
    e: Ambiguity,EntityBag,IntentIR
    Ambiguity:
    EntityBag: get(2)  # Named entities extracted from NL.
    IntentIR: needs_clarification(0)  # Standardized intent representation (nlp2cmd.intent_ir.v1).
  packages/pact-ir/src/pact_ir/target_kind.py:
    e: TargetKind,ExecutionRisk
    TargetKind: propact_protocol(0)
    ExecutionRisk:
  packages/pact-ir/tests/test_ir_roundtrip.py:
    e: test_intent_ir_roundtrip_json,test_execution_plan_from_intent
    test_intent_ir_roundtrip_json()
    test_execution_plan_from_intent()
  scripts/aggregate-example-testql.py:
    e: main
    main()
  scripts/run-example-testql-results.py:
    e: _load_manifest,_testql_dry_run,_testql_ir_parse,_nlp2dsl_run_query,_generate_conversation_toon,_conversation_dry_run,_manifest_consistency,_write_toon_report,process_example,main,Check,ExampleReport
    Check:
    ExampleReport: failures(0),to_dict(0)
    _load_manifest(path)
    _testql_dry_run(commands_path)
    _testql_ir_parse(commands_path)
    _nlp2dsl_run_query(query)
    _generate_conversation_toon(example_id;manifest)
    _conversation_dry_run(conversation_path)
    _manifest_consistency(manifest;artifact_root)
    _write_toon_report(report)
    process_example(example_dir)
    main(argv)
  test_code_generation.py:
    e: test_code_generation
    test_code_generation()
  tests/conftest.py:
  tests/e2e/__init__.py:
  tests/e2e/conftest.py:
    e: _resolve_browser_executable,nlp_client,backend_client,browser_instance,browser_context,page,chat_page
    _resolve_browser_executable()
    nlp_client()
    backend_client()
    browser_instance()
    browser_context(browser_instance)
    page(browser_context)
    chat_page(page)
  tests/e2e/test_backend.py:
    e: test_health,test_workflow_actions_list,test_workflow_actions_contains_send_invoice,test_from_text_dsl_only_no_execute,test_from_text_empty_returns_400,test_from_text_unknown_intent_propagates_error,test_workflow_history_returns_list,test_workflow_history_unknown_id_returns_404,test_chat_start_proxied_to_nlp,test_chat_start_empty_returns_error,test_chat_message_proxied_to_nlp,test_workflow_actions_schema,test_workflow_settings_proxied
    test_health(backend_client)
    test_workflow_actions_list(backend_client)
    test_workflow_actions_contains_send_invoice(backend_client)
    test_from_text_dsl_only_no_execute(backend_client)
    test_from_text_empty_returns_400(backend_client)
    test_from_text_unknown_intent_propagates_error(backend_client)
    test_workflow_history_returns_list(backend_client)
    test_workflow_history_unknown_id_returns_404(backend_client)
    test_chat_start_proxied_to_nlp(backend_client)
    test_chat_start_empty_returns_error(backend_client)
    test_chat_message_proxied_to_nlp(backend_client)
    test_workflow_actions_schema(backend_client)
    test_workflow_settings_proxied(backend_client)
  tests/e2e/test_chat_ui.py:
    e: test_page_title,test_page_has_no_js_errors,test_web_app_manifest,test_tts_button_present,test_tts_button_default_state_active,test_tts_toggle_disables,test_tts_toggle_re_enables,test_speak_function_defined,test_speech_synthesis_available,test_speak_calls_speech_synthesis,test_speak_respects_tts_disabled,test_microphone_get_user_media,test_media_recorder_supported,test_voice_button_present,test_voice_button_initial_text,wait_for_voice_recording,test_voice_transcription_autostarts_on_load,test_voice_button_click_stops_recording,test_text_input_present,test_send_button_present,test_text_message_renders_user_bubble,test_text_message_gets_assistant_response,test_speak_called_on_assistant_response,test_text_input_cleared_after_send,test_status_element_present,test_websocket_connects_on_load
    test_page_title(chat_page)
    test_page_has_no_js_errors(page)
    test_web_app_manifest(chat_page)
    test_tts_button_present(chat_page)
    test_tts_button_default_state_active(chat_page)
    test_tts_toggle_disables(chat_page)
    test_tts_toggle_re_enables(chat_page)
    test_speak_function_defined(chat_page)
    test_speech_synthesis_available(chat_page)
    test_speak_calls_speech_synthesis(chat_page)
    test_speak_respects_tts_disabled(chat_page)
    test_microphone_get_user_media(chat_page)
    test_media_recorder_supported(chat_page)
    test_voice_button_present(chat_page)
    test_voice_button_initial_text(chat_page)
    wait_for_voice_recording(chat_page;timeout_s)
    test_voice_transcription_autostarts_on_load(chat_page)
    test_voice_button_click_stops_recording(chat_page)
    test_text_input_present(chat_page)
    test_send_button_present(chat_page)
    test_text_message_renders_user_bubble(chat_page)
    test_text_message_gets_assistant_response(chat_page)
    test_speak_called_on_assistant_response(chat_page)
    test_text_input_cleared_after_send(chat_page)
    test_status_element_present(chat_page)
    test_websocket_connects_on_load(chat_page)
  tests/e2e/test_nlp_service.py:
    e: test_health,test_nlp_actions_registry,test_parse_known_intent_rules,test_parse_unknown_intent_rules,test_parse_send_email_intent,test_to_dsl_complete_invoice,test_to_dsl_unknown_returns_422,test_chat_start_text,test_chat_start_empty_text_returns_400,test_chat_message_continue_conversation,test_chat_state_get,test_chat_state_not_found,test_actions_schema_all,test_action_schema_by_name,test_action_schema_unknown_returns_404,test_settings_get_all,test_settings_get_llm_section,test_settings_unknown_section_returns_404,test_chat_ui_serves_html
    test_health(nlp_client)
    test_nlp_actions_registry(nlp_client)
    test_parse_known_intent_rules(nlp_client)
    test_parse_unknown_intent_rules(nlp_client)
    test_parse_send_email_intent(nlp_client)
    test_to_dsl_complete_invoice(nlp_client)
    test_to_dsl_unknown_returns_422(nlp_client)
    test_chat_start_text(nlp_client)
    test_chat_start_empty_text_returns_400(nlp_client)
    test_chat_message_continue_conversation(nlp_client)
    test_chat_state_get(nlp_client)
    test_chat_state_not_found(nlp_client)
    test_actions_schema_all(nlp_client)
    test_action_schema_by_name(nlp_client)
    test_action_schema_unknown_returns_404(nlp_client)
    test_settings_get_all(nlp_client)
    test_settings_get_llm_section(nlp_client)
    test_settings_unknown_section_returns_404(nlp_client)
    test_chat_ui_serves_html(nlp_client)
  tests/e2e/test_websocket.py:
    e: _uri,_is_open,_is_closed,test_websocket_connects_and_accepts,test_websocket_unique_conversation_id,test_websocket_accepts_binary_audio,test_websocket_accepts_multiple_chunks,test_websocket_clean_disconnect,test_websocket_server_survives_abrupt_close,test_websocket_concurrent_connections
    _uri(conv_id)
    _is_open(ws)
    _is_closed(ws)
    test_websocket_connects_and_accepts()
    test_websocket_unique_conversation_id()
    test_websocket_accepts_binary_audio()
    test_websocket_accepts_multiple_chunks()
    test_websocket_clean_disconnect()
    test_websocket_server_survives_abrupt_close()
    test_websocket_concurrent_connections()
  tests/test_encoding.py:
    e: test_configure_utf8_reconfigures_stdout,test_configure_utf8_respects_disable,test_configure_utf8_upgrades_ascii_locale,test_utf8_auto_enabled_default
    test_configure_utf8_reconfigures_stdout(monkeypatch)
    test_configure_utf8_respects_disable(monkeypatch)
    test_configure_utf8_upgrades_ascii_locale(monkeypatch)
    test_utf8_auto_enabled_default(monkeypatch)
  tests/test_nlp2dsl_sdk.py:
    e: client_factory,test_from_env_prefers_repo_env_names,test_workflow_and_conversation_endpoints,test_request_retries_transient_server_errors,test_report_helpers_use_report_type_and_schedule,test_new_workflow_helpers_are_data_driven,test_code_generation_methods_hit_expected_services,test_health_queries_all_services,DummyResponse,DummySession
    DummyResponse: __init__(2),raise_for_status(0),json(0)
    DummySession: __init__(1),request(2),close(0)
    client_factory()
    test_from_env_prefers_repo_env_names(monkeypatch)
    test_workflow_and_conversation_endpoints(client_factory)
    test_request_retries_transient_server_errors(client_factory;monkeypatch)
    test_report_helpers_use_report_type_and_schedule(client_factory)
    test_new_workflow_helpers_are_data_driven(client_factory)
    test_code_generation_methods_hit_expected_services(client_factory)
    test_health_queries_all_services(client_factory)
  tests/test_placeholder.py:
    e: test_placeholder,test_import
    test_placeholder()
    test_import()
  tests/test_tests.py:
    e: test_placeholder,test_import
    test_placeholder()
    test_import()
  worker/__init__.py:
  worker/config.py:
    e: WorkerSettings
    WorkerSettings:
  worker/logging_setup.py:
    e: get_request_id,setup_logging,JSONFormatter,RequestIDMiddleware
    JSONFormatter: __init__(1),format(1)  # Emit log records as single-line JSON objects.
    RequestIDMiddleware: __init__(2),dispatch(2)  # Generate or forward X-Request-ID for every HTTP request.
    get_request_id()
    setup_logging(service;level)
  worker/tests/__init__.py:
  worker/tests/conftest.py:
    e: _noop_sleep,mock_asyncio_sleep,client
    _noop_sleep()
    mock_asyncio_sleep()
    client()
  worker/tests/test_worker.py:
    e: client,TestWorkerHealth,TestExecuteActions,TestActionRegistry
    TestWorkerHealth: test_health(1)  # Worker health endpoint.
    TestExecuteActions: test_execute_send_invoice(1),test_execute_send_email(1),test_execute_generate_report(1),test_execute_notify_slack(1),test_execute_notify_telegram(1),test_execute_notify_teams(1),test_execute_unknown_action(1)  # POST /execute — action execution.
    TestActionRegistry: test_handlers_registered(0),test_all_handlers_callable(0)  # ACTION_HANDLERS dict validation.
    client()
  worker/worker.py:
    e: action,_deliver_notification,handle_send_invoice,handle_send_email,handle_generate_report,handle_crm_update,handle_notify_slack,handle_notify_telegram,handle_notify_teams,handle_generate_code,execute_step,health
    action(name)
    _deliver_notification(provider;config;payload;env_var)
    handle_send_invoice(config)
    handle_send_email(config)
    handle_generate_report(config)
    handle_crm_update(config)
    handle_notify_slack(config)
    handle_notify_telegram(config)
    handle_notify_teams(config)
    handle_generate_code(config)
    execute_step(step)
    health()
```

### `project/logic.pl`

```prolog markpact:analysis path=project/logic.pl
% ── Project Metadata ─────────────────────────────────────
project_metadata('nlp2dsl', '0.0.18', 'python').

% ── Project Files ────────────────────────────────────────
project_file('.pfix-test-wrapper.sh', 16, 'shell').
project_file('app.doql.less', 234, 'less').
project_file('backend/app/__init__.py', 1, 'python').
project_file('backend/app/config.py', 43, 'python').
project_file('backend/app/db/__init__.py', 50, 'python').
project_file('backend/app/db/memory.py', 38, 'python').
project_file('backend/app/db/postgres.py', 173, 'python').
project_file('backend/app/engine.py', 270, 'python').
project_file('backend/app/logging_setup.py', 101, 'python').
project_file('backend/app/main.py', 49, 'python').
project_file('backend/app/routers/__init__.py', 1, 'python').
project_file('backend/app/routers/chat.py', 125, 'python').
project_file('backend/app/routers/settings.py', 82, 'python').
project_file('backend/app/routers/system.py', 30, 'python').
project_file('backend/app/routers/workflow.py', 200, 'python').
project_file('backend/app/schemas.py', 65, 'python').
project_file('backend/app/workflow.py', 23, 'python').
project_file('backend/app/workflow_events.py', 92, 'python').
project_file('backend/tests/__init__.py', 1, 'python').
project_file('backend/tests/conftest.py', 32, 'python').
project_file('backend/tests/test_config.py', 83, 'python').
project_file('backend/tests/test_logging.py', 124, 'python').
project_file('backend/tests/test_persistence.py', 185, 'python').
project_file('backend/tests/test_workflow_api.py', 267, 'python').
project_file('examples/01-invoice/main.py', 34, 'python').
project_file('examples/01-invoice/run.sh', 7, 'shell').
project_file('examples/01-invoice/scenario.py', 49, 'python').
project_file('examples/02-email/main.py', 34, 'python').
project_file('examples/02-email/run.sh', 7, 'shell').
project_file('examples/02-email/scenario.py', 58, 'python').
project_file('examples/03-report-and-notify/main.py', 34, 'python').
project_file('examples/03-report-and-notify/run.sh', 7, 'shell').
project_file('examples/03-report-and-notify/scenario.py', 59, 'python').
project_file('examples/04-scheduled-report/main.py', 34, 'python').
project_file('examples/04-scheduled-report/run.sh', 7, 'shell').
project_file('examples/04-scheduled-report/scenario.py', 61, 'python').
project_file('examples/05-conversation-flow/main.py', 34, 'python').
project_file('examples/05-conversation-flow/run.sh', 7, 'shell').
project_file('examples/05-conversation-flow/scenario.py', 45, 'python').
project_file('examples/06-interactive-chat/main.py', 34, 'python').
project_file('examples/06-interactive-chat/scenario.py', 46, 'python').
project_file('examples/07-email-conversation/main.py', 34, 'python').
project_file('examples/07-email-conversation/scenario.py', 37, 'python').
project_file('examples/08-multi-object-benchmark/benchmark_queries.py', 159, 'python').
project_file('examples/08-multi-object-benchmark/main.py', 34, 'python').
project_file('examples/08-multi-object-benchmark/scenario.py', 138, 'python').
project_file('examples/09-execution-smoke/main.py', 34, 'python').
project_file('examples/09-execution-smoke/scenario.py', 45, 'python').
project_file('examples/10-llm-benchmark/main.py', 34, 'python').
project_file('examples/10-llm-benchmark/scenario.py', 38, 'python').
project_file('examples/11-notify-quality/main.py', 34, 'python').
project_file('examples/11-notify-quality/scenario.py', 50, 'python').
project_file('examples/12-ir-show/main.py', 34, 'python').
project_file('examples/12-ir-show/scenario.py', 89, 'python').
project_file('examples/basic/invoice/run.sh', 1, 'shell').
project_file('examples/bootstrap.py', 27, 'python').
project_file('examples/code_generation_examples.py', 26, 'python').
project_file('examples/run-all.sh', 54, 'shell').
project_file('metrun-profile.sh', 49, 'shell').
project_file('nlp-service/app/__init__.py', 1, 'python').
project_file('nlp-service/app/access/__init__.py', 16, 'python').
project_file('nlp-service/app/access/bootstrap.py', 4, 'python').
project_file('nlp-service/app/access/config.py', 4, 'python').
project_file('nlp-service/app/access/native.py', 4, 'python').
project_file('nlp-service/app/access/policy.py', 4, 'python').
project_file('nlp-service/app/access/uri_match.py', 4, 'python').
project_file('nlp-service/app/audio_parser.py', 149, 'python').
project_file('nlp-service/app/code_generator.py', 280, 'python').
project_file('nlp-service/app/config.py', 61, 'python').
project_file('nlp-service/app/conversation/__init__.py', 14, 'python').
project_file('nlp-service/app/conversation/merge.py', 37, 'python').
project_file('nlp-service/app/conversation/orchestrator.py', 108, 'python').
project_file('nlp-service/app/conversation/responses.py', 283, 'python').
project_file('nlp-service/app/dsl/__init__.py', 5, 'python').
project_file('nlp-service/app/dsl/forms.py', 92, 'python').
project_file('nlp-service/app/dsl/mapper.py', 237, 'python').
project_file('nlp-service/app/dsl/pipeline.py', 32, 'python').
project_file('nlp-service/app/execution/__init__.py', 15, 'python').
project_file('nlp-service/app/execution/delegate.py', 30, 'python').
project_file('nlp-service/app/execution/system.py', 343, 'python').
project_file('nlp-service/app/governance/__init__.py', 15, 'python').
project_file('nlp-service/app/governance/bootstrap.py', 79, 'python').
project_file('nlp-service/app/governance/config.py', 166, 'python').
project_file('nlp-service/app/governance/policy.py', 303, 'python').
project_file('nlp-service/app/governance/uri_match.py', 43, 'python').
project_file('nlp-service/app/logging_setup.py', 101, 'python').
project_file('nlp-service/app/main.py', 571, 'python').
project_file('nlp-service/app/mapper.py', 6, 'python').
project_file('nlp-service/app/orchestrator.py', 22, 'python').
project_file('nlp-service/app/parser_enrich.py', 16, 'python').
project_file('nlp-service/app/parser_llm.py', 6, 'python').
project_file('nlp-service/app/parser_rules.py', 6, 'python').
project_file('nlp-service/app/parsing/__init__.py', 4, 'python').
project_file('nlp-service/app/parsing/facade.py', 6, 'python').
project_file('nlp-service/app/registry.py', 404, 'python').
project_file('nlp-service/app/routing/__init__.py', 18, 'python').
project_file('nlp-service/app/routing/intent.py', 56, 'python').
project_file('nlp-service/app/routing/native.py', 144, 'python').
project_file('nlp-service/app/routing/observability.py', 58, 'python').
project_file('nlp-service/app/routing/orientation.py', 380, 'python').
project_file('nlp-service/app/routing/parser/__init__.py', 4, 'python').
project_file('nlp-service/app/routing/parser/enrich.py', 142, 'python').
project_file('nlp-service/app/routing/parser/facade.py', 20, 'python').
project_file('nlp-service/app/routing/parser/llm.py', 146, 'python').
project_file('nlp-service/app/routing/parser/prompt_catalog.py', 83, 'python').
project_file('nlp-service/app/routing/parser/resolve_mode.py', 48, 'python').
project_file('nlp-service/app/routing/parser/rules.py', 565, 'python').
project_file('nlp-service/app/routing/resolve.py', 195, 'python').
project_file('nlp-service/app/schemas.py', 138, 'python').
project_file('nlp-service/app/settings.py', 252, 'python').
project_file('nlp-service/app/store/__init__.py', 31, 'python').
project_file('nlp-service/app/store/factory.py', 47, 'python').
project_file('nlp-service/app/store/memory.py', 24, 'python').
project_file('nlp-service/app/store/redis_store.py', 59, 'python').
project_file('nlp-service/app/system_executor.py', 36, 'python').
project_file('nlp-service/integrations/__init__.py', 6, 'python').
project_file('nlp-service/integrations/loader.py', 63, 'python').
project_file('nlp-service/integrations/mullm/__init__.py', 2, 'python').
project_file('nlp-service/integrations/mullm/registry.py', 67, 'python').
project_file('nlp-service/tests/__init__.py', 1, 'python').
project_file('nlp-service/tests/conftest.py', 102, 'python').
project_file('nlp-service/tests/test_access.py', 75, 'python').
project_file('nlp-service/tests/test_enrich.py', 138, 'python').
project_file('nlp-service/tests/test_execution_delegate.py', 25, 'python').
project_file('nlp-service/tests/test_mapper.py', 295, 'python').
project_file('nlp-service/tests/test_orchestrator.py', 250, 'python').
project_file('nlp-service/tests/test_orientation.py', 107, 'python').
project_file('nlp-service/tests/test_parser_rules.py', 314, 'python').
project_file('nlp-service/tests/test_registry.py', 169, 'python').
project_file('nlp-service/tests/test_routing_observability.py', 42, 'python').
project_file('nlp-service/tests/test_routing_resolve.py', 62, 'python').
project_file('nlp-service/tests/test_store.py', 193, 'python').
project_file('nlp-service/tests/test_system_executor.py', 422, 'python').
project_file('nlp2dsl_sdk/__init__.py', 38, 'python').
project_file('nlp2dsl_sdk/__main__.py', 46, 'python').
project_file('nlp2dsl_sdk/artifacts.py', 411, 'python').
project_file('nlp2dsl_sdk/cli.py', 229, 'python').
project_file('nlp2dsl_sdk/client.py', 601, 'python').
project_file('nlp2dsl_sdk/demos.py', 355, 'python').
project_file('nlp2dsl_sdk/encoding.py', 93, 'python').
project_file('nlp2dsl_sdk/example_loader.py', 40, 'python').
project_file('nlp2dsl_sdk/preview.py', 209, 'python').
project_file('packages/install-dev.sh', 26, 'shell').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/__init__.py', 32, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py', 38, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py', 68, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/domain_mapping.py', 44, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py', 55, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/input.py', 35, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/__init__.py', 13, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', 1210, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py', 229, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/nlp2cmd_convert.py', 48, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/normalize.py', 17, 'python').
project_file('packages/nlp2cmd-intent/src/nlp2cmd_intent/protocols.py', 16, 'python').
project_file('packages/nlp2cmd-intent/tests/test_analyze_query.py', 14, 'python').
project_file('packages/nlp2cmd-intent/tests/test_clarification.py', 32, 'python').
project_file('packages/nlp2cmd-intent/tests/test_intent_pipeline.py', 9, 'python').
project_file('packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py', 44, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/__init__.py', 16, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/pipeline.py', 25, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/router.py', 37, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/__init__.py', 1, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rest_workflow.py', 83, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rule_shell.py', 75, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategy.py', 16, 'python').
project_file('packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py', 51, 'python').
project_file('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 53, 'python').
project_file('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 91, 'python').
project_file('packages/nlp2cmd-planner/tests/test_rest_workflow_propact.py', 34, 'python').
project_file('packages/nlp2cmd-propact/src/nlp2cmd_propact/__init__.py', 17, 'python').
project_file('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', 135, 'python').
project_file('packages/nlp2cmd-propact/src/nlp2cmd_propact/cli.py', 23, 'python').
project_file('packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py', 156, 'python').
project_file('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', 195, 'python').
project_file('packages/nlp2cmd-propact/tests/test_adapter.py', 140, 'python').
project_file('packages/nlp2cmd-propact/tests/test_executor.py', 79, 'python').
project_file('packages/nlp2cmd-propact/tests/test_runner.py', 126, 'python').
project_file('packages/nlp2dsl-show/src/nlp2dsl_show/__init__.py', 4, 'python').
project_file('packages/nlp2dsl-show/src/nlp2dsl_show/cli.py', 92, 'python').
project_file('packages/nlp2dsl-show/src/nlp2dsl_show/encoding.py', 45, 'python').
project_file('packages/nlp2dsl-show/tests/test_cli.py', 48, 'python').
project_file('packages/pact-ir/src/pact_ir/__init__.py', 18, 'python').
project_file('packages/pact-ir/src/pact_ir/execution_plan.py', 60, 'python').
project_file('packages/pact-ir/src/pact_ir/intent.py', 45, 'python').
project_file('packages/pact-ir/src/pact_ir/target_kind.py', 35, 'python').
project_file('packages/pact-ir/tests/test_ir_roundtrip.py', 37, 'python').
project_file('project.sh', 59, 'shell').
project_file('run-all-tests.sh', 45, 'shell').
project_file('scripts/aggregate-example-testql.py', 50, 'python').
project_file('scripts/publish-all.sh', 45, 'shell').
project_file('scripts/run-example-testql-results.py', 365, 'python').
project_file('scripts/setup-dev.sh', 44, 'shell').
project_file('tauri-wrapper/desktop.sh', 80, 'shell').
project_file('tauri-wrapper/scripts/dev.js', 57, 'javascript').
project_file('tauri-wrapper/scripts/serve-dist.js', 140, 'javascript').
project_file('tauri-wrapper/src-tauri/build.rs', 4, 'rust').
project_file('tauri-wrapper/src-tauri/src/main.rs', 8, 'rust').
project_file('tauri-wrapper/test/mvp-voice-chat-wrapper.test.js', 9, 'javascript').
project_file('test_code_generation.py', 140, 'python').
project_file('tests/conftest.py', 11, 'python').
project_file('tests/e2e/__init__.py', 1, 'python').
project_file('tests/e2e/conftest.py', 129, 'python').
project_file('tests/e2e/test_backend.py', 152, 'python').
project_file('tests/e2e/test_chat_ui.py', 263, 'python').
project_file('tests/e2e/test_nlp_service.py', 216, 'python').
project_file('tests/e2e/test_websocket.py', 112, 'python').
project_file('tests/run.sh', 86, 'shell').
project_file('tests/test_encoding.py', 39, 'python').
project_file('tests/test_nlp2dsl_sdk.py', 277, 'python').
project_file('tests/test_placeholder.py', 12, 'python').
project_file('tests/test_tests.py', 12, 'python').
project_file('tree.sh', 2, 'shell').
project_file('worker/__init__.py', 6, 'python').
project_file('worker/config.py', 28, 'python').
project_file('worker/logging_setup.py', 101, 'python').
project_file('worker/tests/__init__.py', 1, 'python').
project_file('worker/tests/conftest.py', 46, 'python').
project_file('worker/tests/test_worker.py', 173, 'python').
project_file('worker/worker.py', 231, 'python').

% ── Python Functions ─────────────────────────────────────
python_function('backend/app/db/__init__.py', 'create_workflow_repo', 0, 2, 3).
python_function('backend/app/engine.py', '_workflow_steps_payload', 1, 2, 1).
python_function('backend/app/engine.py', '_persist_workflow_snapshot', 2, 2, 2).
python_function('backend/app/engine.py', '_publish_workflow_event', 4, 2, 2).
python_function('backend/app/engine.py', '_execute_workflow', 2, 11, 19).
python_function('backend/app/engine.py', '_track_background_task', 1, 1, 5).
python_function('backend/app/engine.py', 'run_workflow', 1, 1, 2).
python_function('backend/app/engine.py', 'start_workflow', 1, 1, 7).
python_function('backend/app/logging_setup.py', 'get_request_id', 0, 1, 1).
python_function('backend/app/logging_setup.py', 'setup_logging', 2, 3, 9).
python_function('backend/app/main.py', 'health', 0, 1, 1).
python_function('backend/app/routers/chat.py', '_proxy_chat_payload', 2, 9, 12).
python_function('backend/app/routers/chat.py', 'chat_start', 1, 2, 4).
python_function('backend/app/routers/chat.py', 'chat_message', 1, 12, 13).
python_function('backend/app/routers/chat.py', 'chat_get_state', 1, 2, 6).
python_function('backend/app/routers/settings.py', 'actions_schema', 0, 1, 4).
python_function('backend/app/routers/settings.py', 'action_schema', 1, 2, 5).
python_function('backend/app/routers/settings.py', 'get_settings', 0, 1, 4).
python_function('backend/app/routers/settings.py', 'get_settings_section', 1, 2, 5).
python_function('backend/app/routers/settings.py', 'update_settings_section', 2, 2, 5).
python_function('backend/app/routers/settings.py', 'set_setting', 1, 2, 5).
python_function('backend/app/routers/settings.py', 'reset_settings', 1, 1, 4).
python_function('backend/app/routers/system.py', 'system_execute', 1, 2, 5).
python_function('backend/app/routers/workflow.py', '_format_sse', 2, 5, 4).
python_function('backend/app/routers/workflow.py', '_workflow_snapshot', 1, 1, 1).
python_function('backend/app/routers/workflow.py', 'orient_nlp', 1, 2, 4).
python_function('backend/app/routers/workflow.py', 'list_actions', 0, 1, 1).
python_function('backend/app/routers/workflow.py', 'run_workflow_endpoint', 1, 1, 2).
python_function('backend/app/routers/workflow.py', 'start_workflow_endpoint', 1, 1, 2).
python_function('backend/app/routers/workflow.py', 'get_history', 0, 1, 2).
python_function('backend/app/routers/workflow.py', 'get_workflow', 1, 2, 3).
python_function('backend/app/routers/workflow.py', 'stream_workflow', 2, 2, 12).
python_function('backend/app/routers/workflow.py', 'workflow_from_text', 1, 8, 12).
python_function('backend/tests/conftest.py', 'client', 0, 1, 2).
python_function('backend/tests/test_workflow_api.py', '_mock_worker_response', 2, 2, 1).
python_function('examples/01-invoice/scenario.py', 'run', 1, 7, 8).
python_function('examples/02-email/scenario.py', 'run', 1, 7, 9).
python_function('examples/03-report-and-notify/scenario.py', 'run', 1, 6, 8).
python_function('examples/04-scheduled-report/scenario.py', 'run', 1, 11, 12).
python_function('examples/05-conversation-flow/scenario.py', 'run_demo', 1, 2, 6).
python_function('examples/05-conversation-flow/scenario.py', 'run_interactive', 1, 1, 2).
python_function('examples/05-conversation-flow/scenario.py', 'run', 1, 2, 2).
python_function('examples/06-interactive-chat/scenario.py', 'run_demo', 1, 3, 6).
python_function('examples/06-interactive-chat/scenario.py', 'run_interactive', 1, 1, 3).
python_function('examples/06-interactive-chat/scenario.py', 'run', 1, 2, 2).
python_function('examples/07-email-conversation/scenario.py', 'run', 1, 3, 8).
python_function('examples/08-multi-object-benchmark/scenario.py', '_extract_actions', 1, 5, 1).
python_function('examples/08-multi-object-benchmark/scenario.py', '_evaluate', 2, 6, 5).
python_function('examples/08-multi-object-benchmark/scenario.py', 'run_benchmark', 1, 16, 11).
python_function('examples/08-multi-object-benchmark/scenario.py', 'run', 1, 5, 11).
python_function('examples/09-execution-smoke/scenario.py', 'run', 1, 9, 9).
python_function('examples/10-llm-benchmark/scenario.py', 'run', 1, 3, 7).
python_function('examples/11-notify-quality/scenario.py', 'run', 1, 8, 9).
python_function('examples/12-ir-show/scenario.py', '_run_show', 1, 8, 5).
python_function('examples/12-ir-show/scenario.py', 'run', 1, 13, 13).
python_function('examples/bootstrap.py', 'bootstrap', 1, 3, 4).
python_function('examples/code_generation_examples.py', 'main', 0, 1, 1).
python_function('nlp-service/app/audio_parser.py', 'stt_audio', 2, 9, 9).
python_function('nlp-service/app/audio_parser.py', 'stt_file', 2, 2, 4).
python_function('nlp-service/app/audio_parser.py', 'is_stt_available', 0, 2, 0).
python_function('nlp-service/app/conversation/merge.py', 'merge_into_state', 2, 13, 4).
python_function('nlp-service/app/conversation/orchestrator.py', 'start_conversation', 1, 1, 6).
python_function('nlp-service/app/conversation/orchestrator.py', 'continue_conversation', 2, 2, 7).
python_function('nlp-service/app/conversation/orchestrator.py', 'get_conversation', 1, 2, 2).
python_function('nlp-service/app/conversation/orchestrator.py', '_attach_routing', 2, 1, 1).
python_function('nlp-service/app/conversation/orchestrator.py', '_process_message', 2, 6, 12).
python_function('nlp-service/app/conversation/responses.py', 'deny_message', 1, 3, 0).
python_function('nlp-service/app/conversation/responses.py', '_execute_keyword_in_text', 2, 3, 4).
python_function('nlp-service/app/conversation/responses.py', '_is_execute_or_continue', 1, 2, 4).
python_function('nlp-service/app/conversation/responses.py', 'check_execute_keyword', 2, 7, 5).
python_function('nlp-service/app/conversation/responses.py', 'handle_unknown_intent', 1, 5, 4).
python_function('nlp-service/app/conversation/responses.py', 'handle_system_action', 1, 7, 7).
python_function('nlp-service/app/conversation/responses.py', 'build_and_check_dsl', 1, 4, 6).
python_function('nlp-service/app/conversation/responses.py', 'build_incomplete_response', 1, 3, 6).
python_function('nlp-service/app/conversation/responses.py', '_nlp_from_state', 1, 5, 5).
python_function('nlp-service/app/conversation/responses.py', 'format_system_result', 2, 3, 3).
python_function('nlp-service/app/conversation/responses.py', '_format_system_status', 1, 1, 1).
python_function('nlp-service/app/conversation/responses.py', '_format_settings_get', 1, 1, 2).
python_function('nlp-service/app/conversation/responses.py', '_format_settings_set', 1, 1, 1).
python_function('nlp-service/app/conversation/responses.py', '_format_settings_reset', 1, 1, 1).
python_function('nlp-service/app/conversation/responses.py', '_format_file_read', 1, 2, 1).
python_function('nlp-service/app/conversation/responses.py', '_format_file_write', 1, 2, 1).
python_function('nlp-service/app/conversation/responses.py', '_format_file_list', 1, 2, 3).
python_function('nlp-service/app/conversation/responses.py', '_format_registry_list', 1, 3, 4).
python_function('nlp-service/app/conversation/responses.py', '_format_registry_update', 1, 1, 1).
python_function('nlp-service/app/dsl/forms.py', 'get_action_form', 1, 5, 5).
python_function('nlp-service/app/dsl/mapper.py', 'map_to_dsl', 1, 8, 14).
python_function('nlp-service/app/dsl/mapper.py', '_resolve_actions', 1, 7, 4).
python_function('nlp-service/app/dsl/mapper.py', '_build_config', 2, 19, 13).
python_function('nlp-service/app/dsl/mapper.py', '_auto_notify_message', 2, 6, 1).
python_function('nlp-service/app/dsl/mapper.py', '_get_field_mapping', 1, 1, 1).
python_function('nlp-service/app/dsl/mapper.py', '_make_name', 2, 3, 2).
python_function('nlp-service/app/dsl/mapper.py', '_build_prompt', 1, 2, 6).
python_function('nlp-service/app/dsl/pipeline.py', 'map_to_dsl_with_enrichment', 1, 6, 3).
python_function('nlp-service/app/execution/delegate.py', 'is_delegated_to_mullm', 1, 2, 1).
python_function('nlp-service/app/execution/delegate.py', 'execution_backend_for_intent', 1, 2, 1).
python_function('nlp-service/app/execution/delegate.py', 'mullm_action_names', 0, 1, 1).
python_function('nlp-service/app/execution/delegate.py', 'delegate_payload', 2, 1, 0).
python_function('nlp-service/app/execution/system.py', '_validate_file_path', 1, 5, 7).
python_function('nlp-service/app/execution/system.py', '_is_read_only', 1, 2, 5).
python_function('nlp-service/app/execution/system.py', 'execute_system_action', 2, 3, 5).
python_function('nlp-service/app/execution/system.py', '_exec_settings_get', 1, 2, 4).
python_function('nlp-service/app/execution/system.py', '_exec_settings_set', 1, 3, 2).
python_function('nlp-service/app/execution/system.py', '_exec_settings_reset', 1, 3, 2).
python_function('nlp-service/app/execution/system.py', '_exec_file_read', 1, 9, 13).
python_function('nlp-service/app/execution/system.py', '_exec_file_write', 1, 4, 10).
python_function('nlp-service/app/execution/system.py', '_exec_file_list', 1, 8, 12).
python_function('nlp-service/app/execution/system.py', '_exec_registry_list', 1, 4, 5).
python_function('nlp-service/app/execution/system.py', '_exec_registry_add', 1, 11, 4).
python_function('nlp-service/app/execution/system.py', '_exec_registry_edit', 1, 12, 5).
python_function('nlp-service/app/execution/system.py', '_exec_status', 1, 3, 2).
python_function('nlp-service/app/governance/bootstrap.py', '_actions_from_yaml_areas', 0, 14, 6).
python_function('nlp-service/app/governance/bootstrap.py', 'apply_yaml_actions', 1, 4, 5).
python_function('nlp-service/app/governance/bootstrap.py', 'bootstrap_registry', 1, 1, 6).
python_function('nlp-service/app/governance/config.py', '_search_paths', 0, 6, 10).
python_function('nlp-service/app/governance/config.py', '_load_yaml_file', 1, 3, 4).
python_function('nlp-service/app/governance/config.py', '_merge_dict', 2, 8, 3).
python_function('nlp-service/app/governance/config.py', 'load_access_config', 0, 3, 2).
python_function('nlp-service/app/governance/config.py', '_load_merged_config', 0, 4, 7).
python_function('nlp-service/app/governance/config.py', '_build_access_config', 2, 7, 9).
python_function('nlp-service/app/governance/config.py', '_enabled_integrations', 1, 7, 3).
python_function('nlp-service/app/governance/config.py', '_default_agent', 2, 3, 2).
python_function('nlp-service/app/governance/config.py', '_allowed_uri_schemes', 1, 3, 2).
python_function('nlp-service/app/governance/config.py', 'get_access_config', 0, 1, 1).
python_function('nlp-service/app/governance/config.py', 'reload_access_config', 0, 1, 1).
python_function('nlp-service/app/governance/policy.py', 'get_agent_id', 1, 4, 3).
python_function('nlp-service/app/governance/policy.py', '_grant_matches', 1, 2, 2).
python_function('nlp-service/app/governance/policy.py', '_grant_action_matches', 2, 4, 3).
python_function('nlp-service/app/governance/policy.py', '_grant_target_matches', 1, 5, 3).
python_function('nlp-service/app/governance/policy.py', '_area_selector_match', 2, 3, 0).
python_function('nlp-service/app/governance/policy.py', '_uri_selector_match', 2, 3, 2).
python_function('nlp-service/app/governance/policy.py', 'authorize_action', 2, 5, 7).
python_function('nlp-service/app/governance/policy.py', '_action_context', 1, 5, 3).
python_function('nlp-service/app/governance/policy.py', '_scheme_decision', 1, 3, 2).
python_function('nlp-service/app/governance/policy.py', '_effect_decision', 4, 4, 1).
python_function('nlp-service/app/governance/policy.py', '_unknown_agent_decision', 2, 4, 1).
python_function('nlp-service/app/governance/policy.py', '_matched_effect', 1, 3, 4).
python_function('nlp-service/app/governance/policy.py', '_decision', 7, 1, 1).
python_function('nlp-service/app/governance/uri_match.py', 'normalize_uri', 1, 2, 1).
python_function('nlp-service/app/governance/uri_match.py', 'uri_matches', 2, 8, 7).
python_function('nlp-service/app/governance/uri_match.py', 'scheme_allowed', 2, 5, 2).
python_function('nlp-service/app/logging_setup.py', 'get_request_id', 0, 1, 1).
python_function('nlp-service/app/logging_setup.py', 'setup_logging', 2, 3, 9).
python_function('nlp-service/app/main.py', 'orient_text', 1, 1, 3).
python_function('nlp-service/app/main.py', 'parse_text', 1, 1, 2).
python_function('nlp-service/app/main.py', 'text_to_dsl', 1, 2, 4).
python_function('nlp-service/app/main.py', 'access_config', 0, 3, 5).
python_function('nlp-service/app/main.py', 'access_check', 5, 3, 3).
python_function('nlp-service/app/main.py', 'access_reload', 0, 2, 2).
python_function('nlp-service/app/main.py', 'list_actions', 0, 2, 4).
python_function('nlp-service/app/main.py', 'health', 0, 3, 8).
python_function('nlp-service/app/main.py', 'chat_start', 2, 5, 10).
python_function('nlp-service/app/main.py', 'chat_message', 3, 5, 10).
python_function('nlp-service/app/main.py', 'chat_state', 1, 2, 4).
python_function('nlp-service/app/main.py', 'actions_schema', 0, 3, 3).
python_function('nlp-service/app/main.py', 'action_schema', 1, 2, 3).
python_function('nlp-service/app/main.py', 'get_settings', 0, 1, 3).
python_function('nlp-service/app/main.py', 'get_settings_section', 1, 2, 3).
python_function('nlp-service/app/main.py', 'update_settings_section', 2, 2, 4).
python_function('nlp-service/app/main.py', 'set_setting', 1, 3, 5).
python_function('nlp-service/app/main.py', 'reset_settings', 1, 1, 3).
python_function('nlp-service/app/main.py', 'system_execute', 1, 2, 6).
python_function('nlp-service/app/main.py', 'generate_code', 1, 2, 4).
python_function('nlp-service/app/main.py', 'get_supported_languages', 0, 2, 3).
python_function('nlp-service/app/main.py', '_run_parser', 1, 3, 3).
python_function('nlp-service/app/main.py', 'websocket_chat', 2, 10, 16).
python_function('nlp-service/app/main.py', 'chat_ui', 0, 2, 5).
python_function('nlp-service/app/registry.py', 'get_action_by_alias', 1, 5, 3).
python_function('nlp-service/app/registry.py', 'get_trigger', 1, 3, 2).
python_function('nlp-service/app/registry.py', 'get_required_fields', 1, 1, 1).
python_function('nlp-service/app/registry.py', 'get_defaults', 1, 1, 2).
python_function('nlp-service/app/registry.py', 'get_quality_required_fields', 1, 1, 2).
python_function('nlp-service/app/routing/native.py', '_match_route', 2, 4, 5).
python_function('nlp-service/app/routing/native.py', '_patterns_match', 2, 3, 3).
python_function('nlp-service/app/routing/native.py', '_pattern_matches', 2, 4, 5).
python_function('nlp-service/app/routing/native.py', '_regex_pattern_matches', 2, 4, 3).
python_function('nlp-service/app/routing/native.py', '_keywords_pattern_matches', 2, 4, 5).
python_function('nlp-service/app/routing/native.py', '_substring_pattern_matches', 2, 4, 4).
python_function('nlp-service/app/routing/native.py', '_aliases_match', 2, 2, 3).
python_function('nlp-service/app/routing/native.py', 'resolve_native_intent', 1, 4, 5).
python_function('nlp-service/app/routing/native.py', '_resolve_configured_route', 3, 5, 4).
python_function('nlp-service/app/routing/native.py', '_route_decision', 3, 2, 1).
python_function('nlp-service/app/routing/native.py', '_resolve_action_alias', 2, 2, 3).
python_function('nlp-service/app/routing/native.py', '_best_action_alias', 2, 3, 3).
python_function('nlp-service/app/routing/native.py', '_best_alias_for_action', 4, 6, 4).
python_function('nlp-service/app/routing/observability.py', 'record_intent_decision', 1, 7, 4).
python_function('nlp-service/app/routing/observability.py', 'routing_metrics_snapshot', 0, 1, 1).
python_function('nlp-service/app/routing/observability.py', 'reset_routing_metrics', 0, 1, 1).
python_function('nlp-service/app/routing/orientation.py', '_has_registry_hint', 1, 2, 2).
python_function('nlp-service/app/routing/orientation.py', '_has_host_hint', 1, 3, 2).
python_function('nlp-service/app/routing/orientation.py', '_is_file_list_query', 1, 5, 4).
python_function('nlp-service/app/routing/orientation.py', '_file_list_scope', 1, 10, 5).
python_function('nlp-service/app/routing/orientation.py', '_host_list_root', 0, 3, 2).
python_function('nlp-service/app/routing/orientation.py', '_normalize_orient_path', 2, 3, 2).
python_function('nlp-service/app/routing/orientation.py', '_resolve_project_host_path', 2, 4, 4).
python_function('nlp-service/app/routing/orientation.py', '_resolve_list_path_remainder', 2, 6, 5).
python_function('nlp-service/app/routing/orientation.py', '_resolve_file_list_host_command', 1, 15, 9).
python_function('nlp-service/app/routing/orientation.py', 'orient_query', 1, 16, 14).
python_function('nlp-service/app/routing/parser/enrich.py', 'is_enrich_enabled', 0, 1, 3).
python_function('nlp-service/app/routing/parser/enrich.py', 'get_enrichable_missing', 1, 5, 3).
python_function('nlp-service/app/routing/parser/enrich.py', 'can_enrich_missing', 1, 4, 4).
python_function('nlp-service/app/routing/parser/enrich.py', 'enrich_entities', 2, 14, 19).
python_function('nlp-service/app/routing/parser/facade.py', 'parse_text', 2, 2, 4).
python_function('nlp-service/app/routing/parser/llm.py', 'parse_llm', 1, 3, 11).
python_function('nlp-service/app/routing/parser/llm.py', '_detect_provider', 0, 10, 1).
python_function('nlp-service/app/routing/parser/llm.py', '_parse_json_response', 1, 6, 7).
python_function('nlp-service/app/routing/parser/prompt_catalog.py', 'build_llm_system_prompt', 0, 8, 8).
python_function('nlp-service/app/routing/parser/resolve_mode.py', 'parse_with_mode', 2, 10, 7).
python_function('nlp-service/app/routing/parser/rules.py', 'parse_rules', 1, 15, 10).
python_function('nlp-service/app/routing/parser/rules.py', '_detect_actions', 1, 6, 6).
python_function('nlp-service/app/routing/parser/rules.py', '_apply_context_filters', 2, 21, 6).
python_function('nlp-service/app/routing/parser/rules.py', '_action_alias_scores', 1, 4, 3).
python_function('nlp-service/app/routing/parser/rules.py', '_alias_in_text', 2, 3, 4).
python_function('nlp-service/app/routing/parser/rules.py', '_longest_alias_match', 2, 4, 4).
python_function('nlp-service/app/routing/parser/rules.py', '_actions_by_score', 1, 1, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_dominant_overlap_action', 2, 4, 4).
python_function('nlp-service/app/routing/parser/rules.py', '_action_category', 1, 1, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_top_system_action_wins', 4, 4, 0).
python_function('nlp-service/app/routing/parser/rules.py', '_second_system_action_wins', 4, 3, 0).
python_function('nlp-service/app/routing/parser/rules.py', '_resolve_intent', 1, 5, 5).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_entities', 2, 1, 13).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_amount', 2, 5, 5).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_email', 2, 3, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_body_content_prefix', 2, 4, 3).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_email_subject_and_body', 2, 8, 3).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_reminder_subject', 2, 4, 4).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_report_type', 2, 3, 1).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_format', 2, 3, 1).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_notification_channels', 2, 10, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_notification_message', 2, 6, 3).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_param_aliases', 2, 5, 5).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_system_entities', 3, 1, 5).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_file_path_entity', 2, 3, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_setting_path_entity', 2, 3, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_model_setting_entity', 2, 5, 1).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_numeric_setting_value', 2, 3, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_mode_setting_entity', 2, 6, 1).
python_function('nlp-service/app/routing/parser/rules.py', '_extract_fallback_recipient', 2, 7, 2).
python_function('nlp-service/app/routing/parser/rules.py', '_set_entity', 3, 3, 2).
python_function('nlp-service/app/routing/resolve.py', '_parser_source', 1, 5, 4).
python_function('nlp-service/app/routing/resolve.py', '_intent_from_native', 1, 3, 3).
python_function('nlp-service/app/routing/resolve.py', '_intent_from_nlp', 2, 2, 4).
python_function('nlp-service/app/routing/resolve.py', '_apply_auth', 2, 4, 1).
python_function('nlp-service/app/routing/resolve.py', '_intent_from_orientation', 2, 4, 6).
python_function('nlp-service/app/routing/resolve.py', 'resolve_intent', 1, 18, 17).
python_function('nlp-service/app/settings.py', '_coerce_type', 2, 5, 5).
python_function('nlp-service/app/store/factory.py', 'get_conversation_store', 0, 4, 5).
python_function('nlp-service/integrations/loader.py', '_integration_names', 0, 5, 4).
python_function('nlp-service/integrations/loader.py', 'load_integration_registries', 0, 5, 8).
python_function('nlp-service/integrations/loader.py', 'apply_integrations', 1, 5, 6).
python_function('nlp-service/tests/conftest.py', 'sample_texts', 0, 1, 0).
python_function('nlp-service/tests/conftest.py', 'expected_intents', 0, 1, 0).
python_function('nlp-service/tests/conftest.py', 'sample_entities', 0, 1, 0).
python_function('nlp-service/tests/conftest.py', 'mock_conversation_store', 0, 1, 1).
python_function('nlp-service/tests/test_access.py', '_point_config', 1, 1, 3).
python_function('nlp-service/tests/test_access.py', 'test_config_loads_areas', 0, 3, 3).
python_function('nlp-service/tests/test_access.py', 'test_uri_match_mullm', 0, 4, 1).
python_function('nlp-service/tests/test_access.py', 'test_files_agent_can_list', 0, 3, 1).
python_function('nlp-service/tests/test_access.py', 'test_mail_agent_denied_mullm_execute', 0, 2, 1).
python_function('nlp-service/tests/test_access.py', 'test_native_lista_plikow_registry', 0, 3, 1).
python_function('nlp-service/tests/test_access.py', 'test_registry_has_yaml_action', 0, 3, 2).
python_function('nlp-service/tests/test_enrich.py', '_enable_enrich', 1, 1, 2).
python_function('nlp-service/tests/test_execution_delegate.py', 'test_mullm_shell_delegated', 0, 3, 2).
python_function('nlp-service/tests/test_execution_delegate.py', 'test_invoice_worker_backend', 0, 2, 1).
python_function('nlp-service/tests/test_execution_delegate.py', 'test_delegate_payload_shape', 0, 3, 1).
python_function('nlp-service/tests/test_orchestrator.py', '_patch_store', 1, 1, 3).
python_function('nlp-service/tests/test_routing_observability.py', '_reset_metrics', 0, 1, 2).
python_function('nlp-service/tests/test_routing_observability.py', 'test_record_increments_rules_hit', 0, 2, 4).
python_function('nlp-service/tests/test_routing_observability.py', 'test_resolve_intent_updates_metrics', 0, 2, 3).
python_function('nlp-service/tests/test_system_executor.py', '_reset_settings', 1, 1, 3).
python_function('nlp2dsl_sdk/__main__.py', 'main', 0, 5, 8).
python_function('nlp2dsl_sdk/artifacts.py', 'example_artifact_root', 1, 1, 2).
python_function('nlp2dsl_sdk/artifacts.py', '_slugify', 1, 2, 4).
python_function('nlp2dsl_sdk/artifacts.py', '_mask_secret', 1, 3, 1).
python_function('nlp2dsl_sdk/artifacts.py', 'collect_environment', 0, 6, 4).
python_function('nlp2dsl_sdk/artifacts.py', 'write_environment_doql', 3, 3, 9).
python_function('nlp2dsl_sdk/artifacts.py', 'build_process_trace', 2, 17, 5).
python_function('nlp2dsl_sdk/artifacts.py', '_action_endpoint', 1, 3, 1).
python_function('nlp2dsl_sdk/artifacts.py', '_action_transport', 1, 3, 1).
python_function('nlp2dsl_sdk/artifacts.py', 'write_query_artifacts', 3, 1, 10).
python_function('nlp2dsl_sdk/artifacts.py', 'write_manifest', 1, 1, 6).
python_function('nlp2dsl_sdk/artifacts.py', 'write_testql_commands', 1, 4, 8).
python_function('nlp2dsl_sdk/artifacts.py', 'write_services_snapshot', 2, 3, 5).
python_function('nlp2dsl_sdk/artifacts.py', '_extract_actions', 1, 4, 2).
python_function('nlp2dsl_sdk/artifacts.py', 'get_example_writer', 0, 2, 3).
python_function('nlp2dsl_sdk/cli.py', '_analyze', 1, 2, 1).
python_function('nlp2dsl_sdk/cli.py', '_display', 1, 13, 5).
python_function('nlp2dsl_sdk/cli.py', 'show', 1, 2, 3).
python_function('nlp2dsl_sdk/cli.py', '_client', 0, 1, 1).
python_function('nlp2dsl_sdk/cli.py', '_health', 0, 2, 5).
python_function('nlp2dsl_sdk/cli.py', '_run', 1, 12, 9).
python_function('nlp2dsl_sdk/cli.py', '_actions', 0, 3, 5).
python_function('nlp2dsl_sdk/cli.py', '_chat_start', 1, 2, 5).
python_function('nlp2dsl_sdk/cli.py', '_demo', 2, 6, 3).
python_function('nlp2dsl_sdk/cli.py', 'main', 1, 7, 13).
python_function('nlp2dsl_sdk/client.py', 'workflow_step', 1, 1, 1).
python_function('nlp2dsl_sdk/demos.py', '_print_code_generation_preview', 1, 3, 3).
python_function('nlp2dsl_sdk/demos.py', 'run_crm_update_demo', 1, 3, 5).
python_function('nlp2dsl_sdk/demos.py', 'run_action_catalog_demo', 1, 6, 9).
python_function('nlp2dsl_sdk/demos.py', 'run_automation_gallery_demo', 1, 4, 5).
python_function('nlp2dsl_sdk/demos.py', 'run_code_generation_demo', 1, 6, 9).
python_function('nlp2dsl_sdk/demos.py', '_run_direct_code_generation', 1, 5, 6).
python_function('nlp2dsl_sdk/demos.py', '_get_supported_languages', 1, 3, 4).
python_function('nlp2dsl_sdk/demos.py', '_run_workflow_code_examples', 1, 1, 1).
python_function('nlp2dsl_sdk/demos.py', '_run_conversation_code_example', 1, 3, 5).
python_function('nlp2dsl_sdk/demos.py', '_run_worker_code_generation', 1, 6, 6).
python_function('nlp2dsl_sdk/demos.py', 'list_available_demos', 0, 1, 0).
python_function('nlp2dsl_sdk/encoding.py', 'utf8_auto_enabled', 0, 1, 3).
python_function('nlp2dsl_sdk/encoding.py', '_explicit_utf8_locale', 0, 4, 2).
python_function('nlp2dsl_sdk/encoding.py', '_apply_utf8_locale_env', 0, 2, 2).
python_function('nlp2dsl_sdk/encoding.py', '_reconfigure_stdio', 0, 4, 2).
python_function('nlp2dsl_sdk/encoding.py', '_set_utf8_locale', 0, 3, 1).
python_function('nlp2dsl_sdk/encoding.py', 'configure_utf8', 0, 3, 4).
python_function('nlp2dsl_sdk/encoding.py', '_auto_configure_once', 0, 2, 1).
python_function('nlp2dsl_sdk/encoding.py', 'utf8_open', 2, 3, 1).
python_function('nlp2dsl_sdk/example_loader.py', 'load_example_runner', 1, 7, 11).
python_function('nlp2dsl_sdk/preview.py', 'print_json', 1, 1, 2).
python_function('nlp2dsl_sdk/preview.py', 'print_workflow_preview', 1, 11, 5).
python_function('nlp2dsl_sdk/preview.py', 'print_execution_result', 1, 5, 5).
python_function('nlp2dsl_sdk/preview.py', 'workflow_http_error_result', 1, 11, 4).
python_function('nlp2dsl_sdk/preview.py', 'preview_text_examples', 3, 9, 8).
python_function('nlp2dsl_sdk/preview.py', 'execute_from_text', 2, 8, 7).
python_function('nlp2dsl_sdk/preview.py', 'execute_text_examples', 3, 8, 8).
python_function('nlp2dsl_sdk/preview.py', 'finalize_example_artifacts', 1, 2, 2).
python_function('nlp2dsl_sdk/preview.py', 'ensure_services', 1, 2, 2).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py', 'clarification_enforced', 0, 1, 3).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py', 'ensure_intent_clear', 1, 4, 3).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py', 'get_user_config_dir', 0, 3, 4).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py', '_package_data_dir', 0, 2, 4).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py', '_nlp2cmd_data_dir', 0, 2, 3).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/data_files.py', 'find_data_files', 0, 6, 10).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/domain_mapping.py', 'domain_to_target_kind', 1, 2, 2).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/domain_mapping.py', 'intent_to_execution_risk', 1, 7, 1).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py', 'default_intent_detector', 0, 1, 1).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/input.py', 'analyze_query', 1, 3, 6).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_query_normalizer', 0, 5, 1).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_polish_support', 0, 4, 0).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_fuzzy_schema_matcher', 0, 7, 5).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_ml_classifier', 0, 8, 5).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_semantic_matcher', 0, 7, 5).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_get_spacy_model', 0, 8, 7).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', '_normalize_url', 1, 8, 3).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py', '_find_data_files', 0, 1, 2).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py', '_normalize_polish_text', 1, 1, 2).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py', '_dedupe_case_insensitive', 1, 3, 4).
python_function('packages/nlp2cmd-intent/src/nlp2cmd_intent/nlp2cmd_convert.py', 'detection_to_intent_ir', 1, 10, 12).
python_function('packages/nlp2cmd-intent/tests/test_analyze_query.py', 'test_analyze_query_find_files', 0, 5, 2).
python_function('packages/nlp2cmd-intent/tests/test_clarification.py', 'test_ensure_intent_clear_blocks_low_confidence', 0, 2, 5).
python_function('packages/nlp2cmd-intent/tests/test_clarification.py', 'test_ensure_intent_clear_allows_confident_intent', 0, 1, 3).
python_function('packages/nlp2cmd-intent/tests/test_clarification.py', 'test_analyze_query_enforces_clarification_with_env', 1, 1, 3).
python_function('packages/nlp2cmd-intent/tests/test_clarification.py', 'test_analyze_query_allows_ambiguous_without_env', 1, 2, 2).
python_function('packages/nlp2cmd-intent/tests/test_intent_pipeline.py', 'test_file_search_intent_with_keyword_detector', 0, 3, 2).
python_function('packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py', 'test_detection_to_intent_ir_shell_find', 0, 5, 3).
python_function('packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py', 'test_detection_to_intent_ir_browser_navigate', 0, 3, 3).
python_function('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rule_shell.py', '_parse_file_search', 1, 10, 4).
python_function('packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py', 'workflow_backend_enabled', 0, 1, 3).
python_function('packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py', 'workflow_backend_url', 0, 1, 2).
python_function('packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py', 'workflow_run_path', 0, 2, 2).
python_function('packages/nlp2cmd-planner/src/nlp2cmd_planner/workflow_backend.py', 'fetch_workflow_from_text', 1, 4, 12).
python_function('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 'test_planning_pipeline_shell_find', 0, 5, 2).
python_function('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 'test_planning_pipeline_shell_find_with_path', 0, 4, 2).
python_function('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 'test_rule_shell_supports_find_intent', 0, 2, 3).
python_function('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 'test_parse_file_search_from_entities', 0, 2, 3).
python_function('packages/nlp2cmd-planner/tests/test_planning_pipeline.py', 'test_unsupported_intent_raises', 0, 1, 4).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', '_intent', 0, 1, 2).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 'test_supports_when_workflow_enabled', 1, 3, 4).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 'test_supports_disabled_without_env', 1, 2, 4).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 'test_plan_builds_rest_workflow_step', 1, 8, 6).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 'test_plan_raises_on_incomplete_workflow', 1, 1, 6).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow.py', 'test_router_prefers_shell_over_rest', 1, 2, 4).
python_function('packages/nlp2cmd-planner/tests/test_rest_workflow_propact.py', 'test_rest_workflow_renders_propact_markdown', 1, 4, 6).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_shell_block', 1, 1, 1).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_rest_block', 3, 2, 4).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_format_json_body', 1, 2, 3).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_mcp_block', 1, 6, 5).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_ws_block', 1, 5, 5).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', '_delegate_block', 1, 4, 2).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', 'step_to_propact_block', 1, 12, 9).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/adapter.py', 'plan_to_propact_markdown', 1, 2, 3).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/cli.py', 'main', 1, 1, 1).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py', 'execution_route', 1, 3, 0).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py', '_single_step_plan', 2, 1, 2).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_propact_fallback_mode', 0, 1, 3).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_resolve_propact_bin', 1, 2, 2).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_propact_available', 1, 1, 2).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_is_shell_only', 1, 3, 2).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_requires_propact', 1, 2, 1).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_shell_command', 2, 3, 3).
python_function('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', '_run_shell_steps', 1, 7, 10).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_shell_plan_to_markdown', 0, 3, 3).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_rest_block_with_json_body', 0, 4, 2).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_mcp_block_from_tool_params', 0, 4, 5).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_mcp_block_from_dsl', 0, 2, 2).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_ws_block_from_url_and_message', 0, 4, 2).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_delegate_block_for_browser', 0, 5, 2).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_delegate_block_for_sql', 0, 3, 2).
python_function('packages/nlp2cmd-propact/tests/test_adapter.py', 'test_mixed_plan_renders_all_block_types', 0, 4, 3).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', '_shell_plan', 0, 1, 2).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', '_browser_plan', 0, 1, 2).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', 'test_execution_route', 0, 4, 2).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', 'test_hybrid_dry_run_includes_routes', 0, 3, 3).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', 'test_hybrid_routes_shell_to_propact', 1, 2, 6).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', 'test_hybrid_routes_browser_to_nlp2cmd', 1, 2, 6).
python_function('packages/nlp2cmd-propact/tests/test_executor.py', 'test_hybrid_stops_on_first_failure', 1, 3, 5).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', '_shell_plan', 1, 1, 2).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_run_dry_run_returns_markdown_only', 0, 5, 4).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_run_executes_propact_without_dry_run', 2, 6, 5).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_shell_fallback_when_propact_missing', 2, 5, 5).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_rest_plan_fails_without_propact', 1, 4, 5).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_shell_fallback_disabled_returns_error', 2, 3, 5).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_shell_fallback_propagates_nonzero_exit', 0, 3, 4).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_empty_plan_fails', 0, 3, 3).
python_function('packages/nlp2cmd-propact/tests/test_runner.py', 'test_propact_bin_env_override', 3, 2, 6).
python_function('packages/nlp2dsl-show/src/nlp2dsl_show/cli.py', '_serialize', 2, 2, 2).
python_function('packages/nlp2dsl-show/src/nlp2dsl_show/cli.py', 'main', 1, 7, 13).
python_function('packages/nlp2dsl-show/src/nlp2dsl_show/cli.py', '_attach_contract_check', 1, 5, 3).
python_function('packages/nlp2dsl-show/tests/test_cli.py', 'test_build_query_structure_intent_only', 0, 5, 1).
python_function('packages/nlp2dsl-show/tests/test_cli.py', 'test_build_query_structure_with_plan', 0, 2, 1).
python_function('packages/nlp2dsl-show/tests/test_cli.py', 'test_cli_show_json', 0, 3, 2).
python_function('packages/nlp2dsl-show/tests/test_cli.py', 'test_cli_show_rejects_ambiguous_query_when_enforced', 0, 3, 1).
python_function('packages/pact-ir/tests/test_ir_roundtrip.py', 'test_intent_ir_roundtrip_json', 0, 3, 3).
python_function('packages/pact-ir/tests/test_ir_roundtrip.py', 'test_execution_plan_from_intent', 0, 4, 4).
python_function('scripts/aggregate-example-testql.py', 'main', 0, 7, 11).
python_function('scripts/run-example-testql-results.py', '_load_manifest', 1, 3, 3).
python_function('scripts/run-example-testql-results.py', '_testql_dry_run', 1, 2, 4).
python_function('scripts/run-example-testql-results.py', '_testql_ir_parse', 1, 4, 4).
python_function('scripts/run-example-testql-results.py', '_nlp2dsl_run_query', 1, 5, 8).
python_function('scripts/run-example-testql-results.py', '_generate_conversation_toon', 2, 6, 7).
python_function('scripts/run-example-testql-results.py', '_conversation_dry_run', 1, 8, 8).
python_function('scripts/run-example-testql-results.py', '_manifest_consistency', 2, 10, 5).
python_function('scripts/run-example-testql-results.py', '_write_toon_report', 1, 4, 5).
python_function('scripts/run-example-testql-results.py', 'process_example', 1, 11, 24).
python_function('scripts/run-example-testql-results.py', 'main', 1, 16, 18).
python_function('test_code_generation.py', 'test_code_generation', 0, 11, 14).
python_function('tests/e2e/conftest.py', '_resolve_browser_executable', 0, 3, 1).
python_function('tests/e2e/conftest.py', 'nlp_client', 0, 1, 1).
python_function('tests/e2e/conftest.py', 'backend_client', 0, 1, 1).
python_function('tests/e2e/conftest.py', 'browser_instance', 0, 2, 5).
python_function('tests/e2e/conftest.py', 'browser_context', 1, 1, 3).
python_function('tests/e2e/conftest.py', 'page', 1, 1, 3).
python_function('tests/e2e/conftest.py', 'chat_page', 1, 2, 5).
python_function('tests/e2e/test_backend.py', 'test_health', 1, 4, 2).
python_function('tests/e2e/test_backend.py', 'test_workflow_actions_list', 1, 7, 4).
python_function('tests/e2e/test_backend.py', 'test_workflow_actions_contains_send_invoice', 1, 4, 2).
python_function('tests/e2e/test_backend.py', 'test_from_text_dsl_only_no_execute', 1, 5, 2).
python_function('tests/e2e/test_backend.py', 'test_from_text_empty_returns_400', 1, 2, 1).
python_function('tests/e2e/test_backend.py', 'test_from_text_unknown_intent_propagates_error', 1, 2, 1).
python_function('tests/e2e/test_backend.py', 'test_workflow_history_returns_list', 1, 3, 3).
python_function('tests/e2e/test_backend.py', 'test_workflow_history_unknown_id_returns_404', 1, 2, 1).
python_function('tests/e2e/test_backend.py', 'test_chat_start_proxied_to_nlp', 1, 4, 2).
python_function('tests/e2e/test_backend.py', 'test_chat_start_empty_returns_error', 1, 2, 1).
python_function('tests/e2e/test_backend.py', 'test_chat_message_proxied_to_nlp', 1, 4, 2).
python_function('tests/e2e/test_backend.py', 'test_workflow_actions_schema', 1, 4, 4).
python_function('tests/e2e/test_backend.py', 'test_workflow_settings_proxied', 1, 3, 2).
python_function('tests/e2e/test_chat_ui.py', 'test_page_title', 1, 3, 2).
python_function('tests/e2e/test_chat_ui.py', 'test_page_has_no_js_errors', 1, 2, 4).
python_function('tests/e2e/test_chat_ui.py', 'test_web_app_manifest', 1, 3, 2).
python_function('tests/e2e/test_chat_ui.py', 'test_tts_button_present', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_tts_button_default_state_active', 1, 3, 3).
python_function('tests/e2e/test_chat_ui.py', 'test_tts_toggle_disables', 1, 3, 4).
python_function('tests/e2e/test_chat_ui.py', 'test_tts_toggle_re_enables', 1, 3, 4).
python_function('tests/e2e/test_chat_ui.py', 'test_speak_function_defined', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_speech_synthesis_available', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_speak_calls_speech_synthesis', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_speak_respects_tts_disabled', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_microphone_get_user_media', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_media_recorder_supported', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_voice_button_present', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_voice_button_initial_text', 1, 2, 2).
python_function('tests/e2e/test_chat_ui.py', 'wait_for_voice_recording', 2, 3, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_voice_transcription_autostarts_on_load', 1, 3, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_voice_button_click_stops_recording', 1, 2, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_text_input_present', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_send_button_present', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_text_message_renders_user_bubble', 1, 2, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_text_message_gets_assistant_response', 1, 2, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_speak_called_on_assistant_response', 1, 3, 5).
python_function('tests/e2e/test_chat_ui.py', 'test_text_input_cleared_after_send', 1, 2, 4).
python_function('tests/e2e/test_chat_ui.py', 'test_status_element_present', 1, 2, 1).
python_function('tests/e2e/test_chat_ui.py', 'test_websocket_connects_on_load', 1, 2, 1).
python_function('tests/e2e/test_nlp_service.py', 'test_health', 1, 7, 4).
python_function('tests/e2e/test_nlp_service.py', 'test_nlp_actions_registry', 1, 8, 5).
python_function('tests/e2e/test_nlp_service.py', 'test_parse_known_intent_rules', 1, 6, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_parse_unknown_intent_rules', 1, 3, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_parse_send_email_intent', 1, 3, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_to_dsl_complete_invoice', 1, 5, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_to_dsl_unknown_returns_422', 1, 3, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_start_text', 1, 5, 3).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_start_empty_text_returns_400', 1, 2, 1).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_message_continue_conversation', 1, 6, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_state_get', 1, 4, 3).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_state_not_found', 1, 2, 1).
python_function('tests/e2e/test_nlp_service.py', 'test_actions_schema_all', 1, 4, 4).
python_function('tests/e2e/test_nlp_service.py', 'test_action_schema_by_name', 1, 3, 5).
python_function('tests/e2e/test_nlp_service.py', 'test_action_schema_unknown_returns_404', 1, 2, 1).
python_function('tests/e2e/test_nlp_service.py', 'test_settings_get_all', 1, 4, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_settings_get_llm_section', 1, 5, 2).
python_function('tests/e2e/test_nlp_service.py', 'test_settings_unknown_section_returns_404', 1, 2, 1).
python_function('tests/e2e/test_nlp_service.py', 'test_chat_ui_serves_html', 1, 4, 2).
python_function('tests/e2e/test_websocket.py', '_uri', 1, 1, 0).
python_function('tests/e2e/test_websocket.py', '_is_open', 1, 1, 0).
python_function('tests/e2e/test_websocket.py', '_is_closed', 1, 1, 0).
python_function('tests/e2e/test_websocket.py', 'test_websocket_connects_and_accepts', 0, 2, 3).
python_function('tests/e2e/test_websocket.py', 'test_websocket_unique_conversation_id', 0, 3, 3).
python_function('tests/e2e/test_websocket.py', 'test_websocket_accepts_binary_audio', 0, 4, 8).
python_function('tests/e2e/test_websocket.py', 'test_websocket_accepts_multiple_chunks', 0, 3, 7).
python_function('tests/e2e/test_websocket.py', 'test_websocket_clean_disconnect', 0, 3, 4).
python_function('tests/e2e/test_websocket.py', 'test_websocket_server_survives_abrupt_close', 0, 2, 5).
python_function('tests/e2e/test_websocket.py', 'test_websocket_concurrent_connections', 0, 4, 7).
python_function('tests/test_encoding.py', 'test_configure_utf8_reconfigures_stdout', 1, 2, 6).
python_function('tests/test_encoding.py', 'test_configure_utf8_respects_disable', 1, 2, 6).
python_function('tests/test_encoding.py', 'test_configure_utf8_upgrades_ascii_locale', 1, 3, 3).
python_function('tests/test_encoding.py', 'test_utf8_auto_enabled_default', 1, 3, 3).
python_function('tests/test_nlp2dsl_sdk.py', 'client_factory', 0, 1, 3).
python_function('tests/test_nlp2dsl_sdk.py', 'test_from_env_prefers_repo_env_names', 1, 5, 3).
python_function('tests/test_nlp2dsl_sdk.py', 'test_workflow_and_conversation_endpoints', 1, 17, 7).
python_function('tests/test_nlp2dsl_sdk.py', 'test_request_retries_transient_server_errors', 2, 4, 7).
python_function('tests/test_nlp2dsl_sdk.py', 'test_report_helpers_use_report_type_and_schedule', 1, 10, 4).
python_function('tests/test_nlp2dsl_sdk.py', 'test_new_workflow_helpers_are_data_driven', 1, 14, 6).
python_function('tests/test_nlp2dsl_sdk.py', 'test_code_generation_methods_hit_expected_services', 1, 16, 7).
python_function('tests/test_nlp2dsl_sdk.py', 'test_health_queries_all_services', 1, 7, 3).
python_function('tests/test_placeholder.py', 'test_placeholder', 0, 2, 0).
python_function('tests/test_placeholder.py', 'test_import', 0, 1, 0).
python_function('tests/test_tests.py', 'test_placeholder', 0, 2, 0).
python_function('tests/test_tests.py', 'test_import', 0, 1, 0).
python_function('worker/logging_setup.py', 'get_request_id', 0, 1, 1).
python_function('worker/logging_setup.py', 'setup_logging', 2, 3, 9).
python_function('worker/tests/conftest.py', '_noop_sleep', 0, 1, 0).
python_function('worker/tests/conftest.py', 'mock_asyncio_sleep', 0, 1, 3).
python_function('worker/tests/conftest.py', 'client', 0, 1, 2).
python_function('worker/tests/test_worker.py', 'client', 0, 1, 2).
python_function('worker/worker.py', 'action', 1, 1, 0).
python_function('worker/worker.py', '_deliver_notification', 4, 5, 8).
python_function('worker/worker.py', 'handle_send_invoice', 1, 1, 6).
python_function('worker/worker.py', 'handle_send_email', 1, 1, 4).
python_function('worker/worker.py', 'handle_generate_report', 1, 1, 6).
python_function('worker/worker.py', 'handle_crm_update', 1, 1, 4).
python_function('worker/worker.py', 'handle_notify_slack', 1, 1, 4).
python_function('worker/worker.py', 'handle_notify_telegram', 1, 1, 4).
python_function('worker/worker.py', 'handle_notify_teams', 1, 1, 4).
python_function('worker/worker.py', 'handle_generate_code', 1, 5, 12).
python_function('worker/worker.py', 'execute_step', 1, 2, 7).
python_function('worker/worker.py', 'health', 0, 1, 3).

% ── Python Classes ───────────────────────────────────────
python_class('backend/app/config.py', 'BackendSettings').
python_class('backend/app/db/__init__.py', 'WorkflowRepo').
python_method('WorkflowRepo', 'save_run', 4, 1, 0).
python_method('WorkflowRepo', 'update_run_status', 2, 1, 0).
python_method('WorkflowRepo', 'get_run', 1, 1, 0).
python_method('WorkflowRepo', 'list_runs', 2, 1, 0).
python_method('WorkflowRepo', 'count_runs', 0, 1, 0).
python_class('backend/app/db/memory.py', 'MemoryWorkflowRepo').
python_method('MemoryWorkflowRepo', '__init__', 1, 1, 1).
python_method('MemoryWorkflowRepo', 'save_run', 4, 2, 3).
python_method('MemoryWorkflowRepo', 'update_run_status', 2, 2, 0).
python_method('MemoryWorkflowRepo', 'get_run', 1, 1, 1).
python_method('MemoryWorkflowRepo', 'list_runs', 2, 1, 3).
python_method('MemoryWorkflowRepo', 'count_runs', 0, 1, 1).
python_class('backend/app/db/postgres.py', 'Base').
python_class('backend/app/db/postgres.py', 'WorkflowRunModel').
python_method('WorkflowRunModel', 'to_dict', 0, 4, 1).
python_class('backend/app/db/postgres.py', 'PostgresWorkflowRepo').
python_method('PostgresWorkflowRepo', '__init__', 1, 2, 4).
python_method('PostgresWorkflowRepo', '_ensure_engine', 0, 3, 2).
python_method('PostgresWorkflowRepo', '_get_session_factory', 0, 1, 1).
python_method('PostgresWorkflowRepo', '_ensure_tables', 0, 2, 4).
python_method('PostgresWorkflowRepo', 'save_run', 4, 1, 11).
python_method('PostgresWorkflowRepo', 'update_run_status', 2, 1, 7).
python_method('PostgresWorkflowRepo', 'get_run', 1, 2, 4).
python_method('PostgresWorkflowRepo', 'list_runs', 2, 3, 7).
python_method('PostgresWorkflowRepo', 'count_runs', 0, 2, 5).
python_method('PostgresWorkflowRepo', 'close', 0, 2, 1).
python_class('backend/app/logging_setup.py', 'JSONFormatter').
python_method('JSONFormatter', '__init__', 1, 1, 2).
python_method('JSONFormatter', 'format', 1, 2, 6).
python_class('backend/app/logging_setup.py', 'RequestIDMiddleware').
python_method('RequestIDMiddleware', '__init__', 2, 1, 2).
python_method('RequestIDMiddleware', 'dispatch', 2, 2, 5).
python_class('backend/app/schemas.py', 'StepStatus').
python_class('backend/app/schemas.py', 'Step').
python_class('backend/app/schemas.py', 'RunWorkflowRequest').
python_class('backend/app/schemas.py', 'StepResult').
python_class('backend/app/schemas.py', 'WorkflowResult').
python_class('backend/app/schemas.py', 'ActionInfo').
python_class('backend/app/workflow_events.py', 'WorkflowEvent').
python_method('WorkflowEvent', 'is_terminal', 0, 1, 0).
python_method('WorkflowEvent', 'to_dict', 0, 1, 1).
python_class('backend/app/workflow_events.py', 'WorkflowEventHub').
python_method('WorkflowEventHub', '__init__', 0, 1, 2).
python_method('WorkflowEventHub', 'subscribe', 1, 1, 2).
python_method('WorkflowEventHub', 'unsubscribe', 2, 3, 3).
python_method('WorkflowEventHub', 'publish', 1, 2, 4).
python_method('WorkflowEventHub', 'subscriber_count', 1, 1, 3).
python_class('backend/tests/test_config.py', 'TestBackendSettingsDefaults').
python_method('TestBackendSettingsDefaults', 'test_worker_url_default', 1, 2, 2).
python_method('TestBackendSettingsDefaults', 'test_nlp_service_url_default', 1, 2, 2).
python_method('TestBackendSettingsDefaults', 'test_postgres_url_default_none', 1, 2, 2).
python_method('TestBackendSettingsDefaults', 'test_log_level_default', 1, 2, 2).
python_class('backend/tests/test_config.py', 'TestBackendSettingsEnvOverride').
python_method('TestBackendSettingsEnvOverride', 'test_worker_url_from_env', 1, 2, 2).
python_method('TestBackendSettingsEnvOverride', 'test_postgres_url_from_env', 1, 2, 2).
python_method('TestBackendSettingsEnvOverride', 'test_log_level_from_env', 1, 2, 2).
python_method('TestBackendSettingsEnvOverride', 'test_extra_env_vars_ignored', 1, 2, 3).
python_class('backend/tests/test_config.py', 'TestBackendSettingsIntegration').
python_method('TestBackendSettingsIntegration', 'test_settings_singleton_importable', 0, 6, 1).
python_method('TestBackendSettingsIntegration', 'test_engine_uses_settings', 0, 3, 0).
python_class('backend/tests/test_logging.py', 'TestJSONFormatter').
python_method('TestJSONFormatter', 'test_format_produces_json', 0, 7, 4).
python_method('TestJSONFormatter', 'test_format_includes_exception', 0, 4, 6).
python_method('TestJSONFormatter', 'test_format_service_name', 0, 3, 4).
python_class('backend/tests/test_logging.py', 'TestRequestIDMiddleware').
python_method('TestRequestIDMiddleware', 'test_app', 0, 1, 3).
python_method('TestRequestIDMiddleware', 'test_response_has_request_id_header', 1, 4, 4).
python_method('TestRequestIDMiddleware', 'test_client_request_id_is_forwarded', 1, 2, 3).
python_method('TestRequestIDMiddleware', 'test_new_id_generated_without_header', 1, 2, 3).
python_class('backend/tests/test_logging.py', 'TestSetupLogging').
python_method('TestSetupLogging', 'test_setup_logging_installs_json_handler', 0, 3, 4).
python_method('TestSetupLogging', 'test_setup_logging_respects_log_level', 0, 2, 2).
python_class('backend/tests/test_persistence.py', 'TestMemoryRepoCRUD').
python_method('TestMemoryRepoCRUD', 'repo', 0, 1, 1).
python_method('TestMemoryRepoCRUD', 'test_save_and_get', 1, 6, 2).
python_method('TestMemoryRepoCRUD', 'test_get_nonexistent', 1, 2, 1).
python_method('TestMemoryRepoCRUD', 'test_update_status', 1, 2, 3).
python_method('TestMemoryRepoCRUD', 'test_update_nonexistent', 1, 1, 1).
python_method('TestMemoryRepoCRUD', 'test_count_empty', 1, 2, 1).
python_method('TestMemoryRepoCRUD', 'test_count_after_saves', 1, 3, 3).
python_class('backend/tests/test_persistence.py', 'TestMemoryRepoListOrdering').
python_method('TestMemoryRepoListOrdering', 'populated_repo', 0, 1, 2).
python_method('TestMemoryRepoListOrdering', 'test_list_default', 1, 5, 2).
python_method('TestMemoryRepoListOrdering', 'test_list_with_limit', 1, 3, 2).
python_method('TestMemoryRepoListOrdering', 'test_list_with_offset', 1, 3, 2).
python_class('backend/tests/test_persistence.py', 'TestMemoryRepoEviction').
python_method('TestMemoryRepoEviction', 'test_eviction_oldest', 0, 8, 5).
python_class('backend/tests/test_persistence.py', 'TestSerializationRoundtrip').
python_method('TestSerializationRoundtrip', 'test_steps_json_roundtrip', 0, 4, 3).
python_class('backend/tests/test_persistence.py', 'TestWorkflowRepoFactory').
python_method('TestWorkflowRepoFactory', 'test_factory_returns_memory_without_postgres', 1, 2, 3).
python_method('TestWorkflowRepoFactory', 'test_factory_returns_postgres_with_url', 1, 3, 4).
python_class('backend/tests/test_workflow_api.py', 'TestHealthEndpoint').
python_method('TestHealthEndpoint', 'test_health_endpoint', 1, 4, 2).
python_class('backend/tests/test_workflow_api.py', 'TestWorkflowActions').
python_method('TestWorkflowActions', 'test_workflow_actions', 1, 7, 4).
python_method('TestWorkflowActions', 'test_workflow_actions_contains_invoice', 1, 3, 2).
python_class('backend/tests/test_workflow_api.py', 'TestRunWorkflow').
python_method('TestRunWorkflow', 'test_run_workflow', 1, 4, 6).
python_method('TestRunWorkflow', 'test_run_workflow_step_failure', 1, 2, 4).
python_method('TestRunWorkflow', 'test_start_workflow', 1, 4, 5).
python_method('TestRunWorkflow', 'test_stream_workflow', 1, 4, 7).
python_class('backend/tests/test_workflow_api.py', 'TestWorkflowHistory').
python_method('TestWorkflowHistory', 'test_workflow_history', 1, 3, 3).
python_class('backend/tests/test_workflow_api.py', 'TestFromText').
python_method('TestFromText', 'test_from_text_complete', 1, 4, 5).
python_method('TestFromText', 'test_from_text_incomplete', 1, 4, 5).
python_method('TestFromText', 'test_from_text_empty', 1, 2, 1).
python_class('examples/08-multi-object-benchmark/benchmark_queries.py', 'BenchmarkQuery').
python_class('nlp-service/app/audio_parser.py', 'StreamingSTT').
python_method('StreamingSTT', '__init__', 1, 2, 1).
python_method('StreamingSTT', 'start', 0, 1, 1).
python_method('StreamingSTT', 'send_audio', 1, 2, 2).
python_method('StreamingSTT', 'get_transcript', 0, 1, 1).
python_method('StreamingSTT', 'stop', 0, 1, 1).
python_class('nlp-service/app/code_generator.py', 'CodeGenerator').
python_method('CodeGenerator', '__init__', 0, 1, 3).
python_method('CodeGenerator', '_get_api_key', 0, 5, 1).
python_method('CodeGenerator', '_build_prompt', 3, 2, 1).
python_method('CodeGenerator', 'generate_code', 4, 14, 12).
python_method('CodeGenerator', '_extract_class_name', 1, 2, 2).
python_method('CodeGenerator', '_split_code_and_tests', 2, 3, 2).
python_method('CodeGenerator', 'get_supported_languages', 0, 1, 2).
python_method('CodeGenerator', 'get_language_info', 1, 1, 1).
python_class('nlp-service/app/config.py', 'NLPServiceSettings').
python_class('nlp-service/app/governance/config.py', 'AccessConfig').
python_method('AccessConfig', 'action_to_area', 0, 6, 1).
python_method('AccessConfig', 'area_by_id', 1, 4, 1).
python_class('nlp-service/app/governance/policy.py', 'AccessDecision').
python_method('AccessDecision', 'to_dict', 0, 1, 0).
python_class('nlp-service/app/governance/policy.py', '_ActionContext').
python_class('nlp-service/app/logging_setup.py', 'JSONFormatter').
python_method('JSONFormatter', '__init__', 1, 1, 2).
python_method('JSONFormatter', 'format', 1, 2, 6).
python_class('nlp-service/app/logging_setup.py', 'RequestIDMiddleware').
python_method('RequestIDMiddleware', '__init__', 2, 1, 2).
python_method('RequestIDMiddleware', 'dispatch', 2, 2, 5).
python_class('nlp-service/app/routing/intent.py', 'IntentDecision').
python_method('IntentDecision', 'to_dict', 0, 1, 0).
python_method('IntentDecision', 'to_nlp_result', 1, 3, 3).
python_class('nlp-service/app/routing/orientation.py', 'OrientationResult').
python_method('OrientationResult', 'to_dict', 0, 1, 0).
python_class('nlp-service/app/schemas.py', 'NLPIntent').
python_class('nlp-service/app/schemas.py', 'NLPEntities').
python_class('nlp-service/app/schemas.py', 'NLPResult').
python_class('nlp-service/app/schemas.py', 'DSLStep').
python_class('nlp-service/app/schemas.py', 'WorkflowDSL').
python_class('nlp-service/app/schemas.py', 'DialogResponse').
python_class('nlp-service/app/schemas.py', 'NLPRequest').
python_class('nlp-service/app/schemas.py', 'OrientRequest').
python_class('nlp-service/app/schemas.py', 'ConversationState').
python_class('nlp-service/app/schemas.py', 'FieldSchema').
python_class('nlp-service/app/schemas.py', 'ActionFormSchema').
python_class('nlp-service/app/schemas.py', 'ConversationResponse').
python_class('nlp-service/app/settings.py', 'LLMSettings').
python_class('nlp-service/app/settings.py', 'NLPSettings').
python_class('nlp-service/app/settings.py', 'WorkerSettings').
python_class('nlp-service/app/settings.py', 'FileAccessSettings').
python_class('nlp-service/app/settings.py', 'SystemSettings').
python_class('nlp-service/app/settings.py', 'SettingsManager').
python_method('SettingsManager', '__new__', 1, 2, 4).
python_method('SettingsManager', 'settings', 0, 1, 0).
python_method('SettingsManager', 'get', 1, 5, 4).
python_method('SettingsManager', 'get_section', 1, 3, 3).
python_method('SettingsManager', 'get_all', 0, 1, 1).
python_method('SettingsManager', 'set', 2, 4, 10).
python_method('SettingsManager', 'update_section', 2, 6, 9).
python_method('SettingsManager', 'reset', 1, 3, 6).
python_method('SettingsManager', '_load', 0, 3, 7).
python_method('SettingsManager', '_save', 0, 2, 5).
python_method('SettingsManager', 'describe', 0, 1, 1).
python_class('nlp-service/app/store/__init__.py', 'ConversationStore').
python_method('ConversationStore', 'get', 1, 1, 0).
python_method('ConversationStore', 'save', 2, 1, 0).
python_method('ConversationStore', 'delete', 1, 1, 0).
python_method('ConversationStore', 'count', 0, 1, 0).
python_class('nlp-service/app/store/memory.py', 'MemoryConversationStore').
python_method('MemoryConversationStore', '__init__', 0, 1, 0).
python_method('MemoryConversationStore', 'get', 1, 1, 1).
python_method('MemoryConversationStore', 'save', 2, 1, 0).
python_method('MemoryConversationStore', 'delete', 1, 1, 1).
python_method('MemoryConversationStore', 'count', 0, 1, 1).
python_class('nlp-service/app/store/redis_store.py', 'RedisConversationStore').
python_method('RedisConversationStore', '__init__', 2, 1, 1).
python_method('RedisConversationStore', '_key', 1, 1, 0).
python_method('RedisConversationStore', 'get', 1, 3, 4).
python_method('RedisConversationStore', 'save', 2, 1, 5).
python_method('RedisConversationStore', 'delete', 1, 1, 3).
python_method('RedisConversationStore', 'count', 0, 1, 1).
python_method('RedisConversationStore', 'close', 0, 1, 1).
python_class('nlp-service/tests/test_enrich.py', '_FakeMessage').
python_method('_FakeMessage', '__init__', 1, 1, 0).
python_class('nlp-service/tests/test_enrich.py', '_FakeChoice').
python_method('_FakeChoice', '__init__', 1, 1, 1).
python_class('nlp-service/tests/test_enrich.py', '_FakeResponse').
python_method('_FakeResponse', '__init__', 1, 1, 1).
python_class('nlp-service/tests/test_enrich.py', 'TestEnrichHelpers').
python_method('TestEnrichHelpers', 'test_is_enrich_enabled', 1, 3, 2).
python_method('TestEnrichHelpers', 'test_get_enrichable_missing_body_only', 0, 2, 1).
python_method('TestEnrichHelpers', 'test_get_enrichable_missing_ignores_required', 0, 2, 1).
python_method('TestEnrichHelpers', 'test_can_enrich_only_quality_fields', 1, 4, 1).
python_class('nlp-service/tests/test_enrich.py', 'TestEnrichEntities').
python_method('TestEnrichEntities', 'test_enrich_fills_email_body', 2, 3, 6).
python_method('TestEnrichEntities', 'test_enrich_disabled_returns_none', 1, 2, 5).
python_method('TestEnrichEntities', 'test_enrich_fills_notify_message', 2, 3, 7).
python_class('nlp-service/tests/test_enrich.py', 'TestEnrichPipeline').
python_method('TestEnrichPipeline', 'test_pipeline_completes_after_enrich', 2, 5, 6).
python_class('nlp-service/tests/test_mapper.py', 'TestMapCompleteDSL').
python_method('TestMapCompleteDSL', 'test_map_complete_invoice', 0, 7, 5).
python_method('TestMapCompleteDSL', 'test_map_complete_email', 0, 5, 4).
python_method('TestMapCompleteDSL', 'test_map_incomplete_email_missing_body', 0, 4, 6).
python_class('nlp-service/tests/test_mapper.py', 'TestMapIncomplete').
python_method('TestMapIncomplete', 'test_map_incomplete_invoice', 0, 6, 6).
python_method('TestMapIncomplete', 'test_map_composite_invoice_email_separate_recipients', 0, 6, 5).
python_class('nlp-service/tests/test_mapper.py', 'TestMapComposite').
python_method('TestMapComposite', 'test_map_composite_report_email', 0, 6, 5).
python_class('nlp-service/tests/test_mapper.py', 'TestMapUnknown').
python_method('TestMapUnknown', 'test_map_unknown_intent', 0, 3, 4).
python_method('TestMapUnknown', 'test_map_nonexistent_intent', 0, 2, 4).
python_class('nlp-service/tests/test_mapper.py', 'TestMapDefaults').
python_method('TestMapDefaults', 'test_map_with_defaults', 0, 3, 5).
python_class('nlp-service/tests/test_mapper.py', 'TestMapTrigger').
python_method('TestMapTrigger', 'test_map_trigger_propagation', 0, 3, 4).
python_class('nlp-service/tests/test_mapper.py', 'TestMapSystemAction').
python_method('TestMapSystemAction', 'test_map_system_action_settings', 0, 2, 4).
python_class('nlp-service/tests/test_mapper.py', 'TestMapAllBusinessActions').
python_method('TestMapAllBusinessActions', 'test_map_all_business_actions', 1, 14, 8).
python_class('nlp-service/tests/test_mapper.py', 'TestResolveActions').
python_method('TestResolveActions', 'test_resolve_direct_action', 0, 2, 1).
python_method('TestResolveActions', 'test_resolve_composite_intent', 0, 3, 1).
python_method('TestResolveActions', 'test_resolve_dynamic_composite', 0, 3, 1).
python_method('TestResolveActions', 'test_resolve_unknown', 0, 2, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestStartConversation').
python_method('TestStartConversation', 'test_start_conversation_complete', 0, 6, 2).
python_method('TestStartConversation', 'test_start_conversation_incomplete', 0, 4, 2).
python_method('TestStartConversation', 'test_start_conversation_unknown', 0, 3, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestExecuteKeywordMatching').
python_method('TestExecuteKeywordMatching', 'test_go_not_matched_inside_zgodnie', 0, 3, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestContinueConversation').
python_method('TestContinueConversation', 'test_continue_conversation', 0, 5, 2).
python_method('TestContinueConversation', 'test_continue_conversation_lazy_create', 0, 3, 1).
python_method('TestContinueConversation', 'test_continue_conversation_email_body', 0, 6, 4).
python_class('nlp-service/tests/test_orchestrator.py', 'TestSystemCommands').
python_method('TestSystemCommands', 'test_system_command_status', 0, 3, 1).
python_method('TestSystemCommands', 'test_system_command_settings', 0, 3, 2).
python_method('TestSystemCommands', 'test_format_system_file_list', 0, 2, 1).
python_method('TestSystemCommands', 'test_format_system_failed_result', 0, 2, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestGetConversation').
python_method('TestGetConversation', 'test_get_conversation_exists', 0, 3, 2).
python_method('TestGetConversation', 'test_get_conversation_not_found', 0, 2, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestGetActionForm').
python_method('TestGetActionForm', 'test_action_form_send_invoice', 0, 6, 1).
python_method('TestGetActionForm', 'test_action_form_nonexistent', 0, 2, 1).
python_class('nlp-service/tests/test_orchestrator.py', 'TestMergeIntoState').
python_method('TestMergeIntoState', 'test_merge_updates_intent', 0, 3, 5).
python_method('TestMergeIntoState', 'test_merge_preserves_existing', 0, 4, 5).
python_class('nlp-service/tests/test_orientation.py', 'TestOrientQuery').
python_method('TestOrientQuery', 'test_lista_plikow_usera_host_default_mullm', 0, 5, 1).
python_method('TestOrientQuery', 'test_lista_plikow_github_path_hint', 0, 4, 1).
python_method('TestOrientQuery', 'test_lista_plikow_systemu_root_fs', 0, 5, 1).
python_method('TestOrientQuery', 'test_lista_plikow_linux_host_home', 0, 4, 1).
python_method('TestOrientQuery', 'test_lista_plikow_root_slash', 0, 4, 1).
python_method('TestOrientQuery', 'test_lista_plikow_projektu_nlp2cmd', 0, 5, 1).
python_method('TestOrientQuery', 'test_lista_plikow_w_github_multi_segment', 0, 4, 1).
python_method('TestOrientQuery', 'test_lista_plikow_projektu_only', 0, 4, 1).
python_method('TestOrientQuery', 'test_lista_plikow_usera_registry', 0, 3, 1).
python_method('TestOrientQuery', 'test_pokaz_pliki_local_connector', 0, 3, 1).
python_method('TestOrientQuery', 'test_run_prefix_shell', 0, 3, 1).
python_method('TestOrientQuery', 'test_disk_space_shell_nl', 0, 2, 1).
python_method('TestOrientQuery', 'test_invoice_workflow_hint', 0, 2, 1).
python_class('nlp-service/tests/test_orientation.py', 'TestResolveIntentOrientation').
python_method('TestResolveIntentOrientation', 'test_lista_plikow_usera_short_circuit_shell', 0, 7, 1).
python_method('TestResolveIntentOrientation', 'test_registry_list_short_circuit_mullm_files', 0, 4, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseInvoice').
python_method('TestParseInvoice', 'test_parse_invoice_simple', 0, 6, 1).
python_method('TestParseInvoice', 'test_parse_invoice_missing_data', 0, 4, 1).
python_method('TestParseInvoice', 'test_parse_invoice_eur', 0, 5, 1).
python_method('TestParseInvoice', 'test_parse_invoice_usd', 0, 5, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseEmail').
python_method('TestParseEmail', 'test_parse_email', 0, 3, 1).
python_method('TestParseEmail', 'test_parse_email_english', 0, 3, 1).
python_method('TestParseEmail', 'test_parse_email_reminder', 0, 5, 1).
python_method('TestParseEmail', 'test_parse_email_with_subject', 0, 4, 1).
python_method('TestParseEmail', 'test_parse_email_colon_body', 0, 4, 1).
python_method('TestParseEmail', 'test_parse_body_content_prefix', 0, 3, 1).
python_method('TestParseEmail', 'test_parse_body_content_prefix_long_form', 0, 3, 1).
python_method('TestParseEmail', 'test_parse_email_offer', 0, 5, 1).
python_method('TestParseEmail', 'test_parse_slack_with_message', 0, 4, 1).
python_method('TestParseEmail', 'test_parse_slack_about_message', 0, 3, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseNotifyQuality').
python_method('TestParseNotifyQuality', 'test_notify_channel_only_maps_incomplete_without_message', 0, 4, 3).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseReport').
python_method('TestParseReport', 'test_parse_report_weekly', 0, 4, 1).
python_method('TestParseReport', 'test_parse_report_hr_xlsx_no_false_system', 0, 4, 1).
python_method('TestParseReport', 'test_parse_report_finance_csv', 0, 4, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseComposite').
python_method('TestParseComposite', 'test_parse_composite_invoice_notify', 0, 4, 1).
python_method('TestParseComposite', 'test_parse_composite_full_flow', 0, 3, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseSystem').
python_method('TestParseSystem', 'test_parse_system_settings', 0, 2, 1).
python_method('TestParseSystem', 'test_parse_system_file_list', 0, 2, 1).
python_method('TestParseSystem', 'test_parse_system_status', 0, 2, 1).
python_method('TestParseSystem', 'test_parse_system_help', 0, 2, 1).
python_method('TestParseSystem', 'test_parse_system_set_model', 0, 4, 1).
python_method('TestParseSystem', 'test_parse_system_set_mode', 0, 4, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestParseUnknown').
python_method('TestParseUnknown', 'test_parse_unknown', 0, 3, 1).
python_class('nlp-service/tests/test_parser_rules.py', 'TestAmountExtraction').
python_method('TestAmountExtraction', 'test_parse_amount_extraction', 3, 3, 2).
python_class('nlp-service/tests/test_parser_rules.py', 'TestTriggerDetection').
python_method('TestTriggerDetection', 'test_parse_trigger_detection', 2, 2, 2).
python_class('nlp-service/tests/test_parser_rules.py', 'TestResultStructure').
python_method('TestResultStructure', 'test_result_is_nlp_result', 0, 5, 3).
python_method('TestResultStructure', 'test_raw_text_preserved', 0, 2, 1).
python_class('nlp-service/tests/test_registry.py', 'TestRegistryStructure').
python_method('TestRegistryStructure', 'test_registry_entry_has_required_keys', 1, 7, 4).
python_class('nlp-service/tests/test_registry.py', 'TestAliasResolution').
python_method('TestAliasResolution', 'test_alias_invoice_pl', 0, 2, 1).
python_method('TestAliasResolution', 'test_alias_email_en', 0, 2, 1).
python_method('TestAliasResolution', 'test_alias_report', 0, 2, 1).
python_method('TestAliasResolution', 'test_alias_slack', 0, 2, 1).
python_method('TestAliasResolution', 'test_alias_unknown', 0, 2, 1).
python_method('TestAliasResolution', 'test_alias_best_match', 0, 2, 1).
python_class('nlp-service/tests/test_registry.py', 'TestTriggerDetection').
python_method('TestTriggerDetection', 'test_trigger_daily', 0, 2, 1).
python_method('TestTriggerDetection', 'test_trigger_weekly', 0, 2, 1).
python_method('TestTriggerDetection', 'test_trigger_monthly', 0, 2, 1).
python_method('TestTriggerDetection', 'test_trigger_manual_default', 0, 2, 1).
python_class('nlp-service/tests/test_registry.py', 'TestHelperFunctions').
python_method('TestHelperFunctions', 'test_get_required_fields_invoice', 0, 3, 1).
python_method('TestHelperFunctions', 'test_get_required_fields_unknown', 0, 2, 1).
python_method('TestHelperFunctions', 'test_get_defaults_invoice', 0, 2, 2).
python_method('TestHelperFunctions', 'test_get_defaults_unknown', 0, 2, 1).
python_class('nlp-service/tests/test_registry.py', 'TestCategories').
python_method('TestCategories', 'test_system_actions_nonempty', 0, 2, 1).
python_method('TestCategories', 'test_business_actions_nonempty', 0, 2, 1).
python_method('TestCategories', 'test_no_overlap', 0, 5, 1).
python_method('TestCategories', 'test_union_is_complete', 0, 2, 2).
python_method('TestCategories', 'test_mullm_actions_loaded', 0, 3, 0).
python_class('nlp-service/tests/test_registry.py', 'TestCompositeIntents').
python_method('TestCompositeIntents', 'test_composite_actions_exist', 1, 3, 2).
python_class('nlp-service/tests/test_routing_resolve.py', 'TestParserSource').
python_method('TestParserSource', 'test_rules_mode', 1, 2, 2).
python_class('nlp-service/tests/test_routing_resolve.py', 'TestResolveIntent').
python_method('TestResolveIntent', 'test_invoice_rules_path', 0, 6, 2).
python_method('TestResolveIntent', 'test_unknown_intent', 0, 4, 1).
python_method('TestResolveIntent', 'test_native_file_list_route', 0, 4, 1).
python_method('TestResolveIntent', 'test_decision_serializable', 0, 4, 2).
python_class('nlp-service/tests/test_routing_resolve.py', 'TestOrchestratorRoutingField').
python_method('TestOrchestratorRoutingField', 'test_start_conversation_includes_routing', 1, 4, 4).
python_class('nlp-service/tests/test_store.py', 'TestMemoryStoreCRUD').
python_method('TestMemoryStoreCRUD', 'store', 0, 1, 1).
python_method('TestMemoryStoreCRUD', 'test_save_and_get', 1, 2, 2).
python_method('TestMemoryStoreCRUD', 'test_get_nonexistent', 1, 2, 1).
python_method('TestMemoryStoreCRUD', 'test_save_overwrites', 1, 2, 2).
python_method('TestMemoryStoreCRUD', 'test_delete', 1, 2, 3).
python_method('TestMemoryStoreCRUD', 'test_delete_nonexistent', 1, 1, 1).
python_method('TestMemoryStoreCRUD', 'test_count_empty', 1, 2, 1).
python_method('TestMemoryStoreCRUD', 'test_count_after_saves', 1, 2, 2).
python_method('TestMemoryStoreCRUD', 'test_count_after_delete', 1, 2, 3).
python_class('nlp-service/tests/test_store.py', 'TestSerializationRoundtrip').
python_method('TestSerializationRoundtrip', 'store', 0, 1, 1).
python_method('TestSerializationRoundtrip', 'test_conversation_state_roundtrip', 1, 7, 5).
python_method('TestSerializationRoundtrip', 'test_complex_entities_roundtrip', 1, 3, 2).
python_class('nlp-service/tests/test_store.py', 'TestStoreFactory').
python_method('TestStoreFactory', 'test_factory_returns_memory_without_redis', 1, 2, 3).
python_method('TestStoreFactory', 'test_factory_singleton', 1, 2, 2).
python_method('TestStoreFactory', 'test_factory_falls_back_on_bad_redis', 1, 2, 2).
python_class('nlp-service/tests/test_store.py', 'TestStoreIsolation').
python_method('TestStoreIsolation', 'test_separate_instances_isolated', 0, 4, 4).
python_class('nlp-service/tests/test_system_executor.py', 'TestSettingsGet').
python_method('TestSettingsGet', 'test_settings_get_all', 0, 5, 1).
python_method('TestSettingsGet', 'test_settings_get_section', 0, 3, 1).
python_method('TestSettingsGet', 'test_settings_get_default_is_all', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestSettingsSet').
python_method('TestSettingsSet', 'test_settings_set_and_verify', 0, 4, 2).
python_method('TestSettingsSet', 'test_settings_set_missing_path', 0, 2, 1).
python_method('TestSettingsSet', 'test_settings_set_missing_value', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestSettingsReset').
python_method('TestSettingsReset', 'test_settings_reset', 0, 4, 3).
python_method('TestSettingsReset', 'test_settings_reset_section', 0, 3, 3).
python_class('nlp-service/tests/test_system_executor.py', 'TestFileList').
python_method('TestFileList', 'test_file_list', 2, 5, 5).
python_method('TestFileList', 'test_file_list_nonexistent', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestRegistryList').
python_method('TestRegistryList', 'test_registry_list', 0, 5, 1).
python_method('TestRegistryList', 'test_registry_list_business', 0, 3, 2).
python_method('TestRegistryList', 'test_registry_list_system', 0, 3, 2).
python_class('nlp-service/tests/test_system_executor.py', 'TestRegistryAdd').
python_method('TestRegistryAdd', 'test_registry_add', 0, 3, 3).
python_method('TestRegistryAdd', 'test_registry_add_missing_name', 0, 2, 1).
python_method('TestRegistryAdd', 'test_registry_add_duplicate', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestStatus').
python_method('TestStatus', 'test_status', 0, 7, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestRegistryEdit').
python_method('TestRegistryEdit', 'test_registry_edit_description', 0, 3, 3).
python_method('TestRegistryEdit', 'test_registry_edit_nonexistent', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestFileRead').
python_method('TestFileRead', 'test_file_read_existing', 2, 4, 4).
python_method('TestFileRead', 'test_file_read_nonexistent', 2, 2, 3).
python_method('TestFileRead', 'test_file_read_no_path', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestFileWrite').
python_method('TestFileWrite', 'test_file_write_new', 2, 3, 5).
python_method('TestFileWrite', 'test_file_write_append', 2, 3, 6).
python_class('nlp-service/tests/test_system_executor.py', 'TestExecuteSystemAction').
python_method('TestExecuteSystemAction', 'test_execute_known_action', 0, 3, 1).
python_method('TestExecuteSystemAction', 'test_execute_unknown_action', 0, 2, 1).
python_class('nlp-service/tests/test_system_executor.py', 'TestFilePathValidation').
python_method('TestFilePathValidation', 'test_validate_allowed_path', 2, 2, 5).
python_method('TestFilePathValidation', 'test_validate_disallowed_path', 0, 1, 2).
python_method('TestFilePathValidation', 'test_is_read_only', 2, 3, 3).
python_class('nlp-service/tests/test_system_executor.py', 'TestExecutorMapping').
python_method('TestExecutorMapping', 'test_all_system_actions_have_executor', 0, 3, 2).
python_method('TestExecutorMapping', 'test_executors_count', 0, 2, 1).
python_class('nlp2dsl_sdk/artifacts.py', 'ExampleArtifactWriter').
python_method('ExampleArtifactWriter', '__init__', 1, 5, 6).
python_method('ExampleArtifactWriter', 'record', 2, 1, 4).
python_method('ExampleArtifactWriter', 'finalize', 1, 4, 6).
python_class('nlp2dsl_sdk/client.py', 'NLP2DSLClient').
python_method('NLP2DSLClient', '__init__', 5, 2, 3).
python_method('NLP2DSLClient', 'from_env', 2, 1, 4).
python_method('NLP2DSLClient', 'close', 0, 2, 1).
python_method('NLP2DSLClient', '__enter__', 0, 1, 0).
python_method('NLP2DSLClient', '__exit__', 3, 1, 1).
python_method('NLP2DSLClient', '_request', 3, 9, 12).
python_method('NLP2DSLClient', '_backend', 2, 1, 1).
python_method('NLP2DSLClient', '_nlp_service', 2, 1, 1).
python_method('NLP2DSLClient', '_worker', 2, 1, 1).
python_method('NLP2DSLClient', 'backend_health', 0, 1, 2).
python_method('NLP2DSLClient', 'nlp_service_health', 0, 1, 2).
python_method('NLP2DSLClient', 'worker_health', 0, 1, 2).
python_method('NLP2DSLClient', 'health', 0, 1, 3).
python_method('NLP2DSLClient', 'workflow_from_text', 3, 1, 2).
python_method('NLP2DSLClient', 'run_workflow', 4, 3, 3).
python_method('NLP2DSLClient', 'workflow_actions', 0, 1, 2).
python_method('NLP2DSLClient', 'workflow_action_schema', 1, 2, 2).
python_method('NLP2DSLClient', 'settings', 0, 1, 2).
python_method('NLP2DSLClient', 'settings_section', 1, 1, 2).
python_method('NLP2DSLClient', 'update_settings_section', 2, 1, 3).
python_method('NLP2DSLClient', 'set_setting', 2, 1, 2).
python_method('NLP2DSLClient', 'reset_settings', 1, 2, 3).
python_method('NLP2DSLClient', 'chat_start', 2, 2, 4).
python_method('NLP2DSLClient', 'chat_message', 3, 2, 4).
python_method('NLP2DSLClient', 'chat_state', 1, 1, 2).
python_method('NLP2DSLClient', 'nlp_chat_start', 2, 2, 4).
python_method('NLP2DSLClient', 'nlp_chat_message', 3, 2, 4).
python_method('NLP2DSLClient', 'nlp_chat_state', 1, 1, 2).
python_method('NLP2DSLClient', 'generate_code', 4, 1, 2).
python_method('NLP2DSLClient', 'supported_languages', 0, 1, 2).
python_method('NLP2DSLClient', 'worker_execute', 3, 1, 3).
python_method('NLP2DSLClient', 'worker_generate_code', 5, 1, 1).
python_method('NLP2DSLClient', 'send_invoice', 5, 1, 2).
python_method('NLP2DSLClient', 'send_email', 5, 3, 2).
python_method('NLP2DSLClient', 'generate_report', 4, 1, 2).
python_method('NLP2DSLClient', 'generate_report_and_notify', 7, 4, 3).
python_method('NLP2DSLClient', 'create_scheduled_report', 7, 1, 1).
python_method('NLP2DSLClient', 'notify_slack', 4, 2, 2).
python_method('NLP2DSLClient', 'crm_update', 4, 2, 3).
python_method('NLP2DSLClient', 'send_invoice_and_notify', 7, 4, 3).
python_class('nlp2dsl_sdk/client.py', 'ConversationFlow').
python_method('ConversationFlow', '__init__', 1, 2, 1).
python_method('ConversationFlow', 'start', 2, 1, 4).
python_method('ConversationFlow', 'send_message', 2, 2, 5).
python_method('ConversationFlow', '_handle_response', 1, 5, 6).
python_method('ConversationFlow', '_handle_in_progress_response', 2, 6, 3).
python_method('ConversationFlow', '_handle_ready_response', 2, 4, 5).
python_method('ConversationFlow', '_handle_completed_response', 2, 4, 2).
python_method('ConversationFlow', '_handle_error_response', 1, 1, 1).
python_method('ConversationFlow', 'run_demo', 0, 2, 5).
python_method('ConversationFlow', 'run_interactive', 0, 6, 6).
python_class('nlp2dsl_sdk/demos.py', 'DemoSpec').
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/clarification.py', 'IntentClarificationRequired').
python_method('IntentClarificationRequired', '__init__', 1, 4, 4).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py', 'PassthroughEntityExtractor').
python_method('PassthroughEntityExtractor', 'extract', 1, 1, 1).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py', 'KeywordIntentAdapter').
python_method('KeywordIntentAdapter', '__init__', 1, 4, 1).
python_method('KeywordIntentAdapter', 'detect', 1, 2, 4).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/facade.py', 'IntentPipeline').
python_method('IntentPipeline', '__init__', 0, 4, 3).
python_method('IntentPipeline', 'run', 1, 2, 6).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', 'DetectionResult').
python_method('DetectionResult', '__post_init__', 0, 3, 0).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py', 'KeywordIntentDetector').
python_method('KeywordIntentDetector', '__init__', 3, 5, 3).
python_method('KeywordIntentDetector', 'add_pattern', 3, 1, 1).
python_method('KeywordIntentDetector', 'detect', 1, 17, 16).
python_method('KeywordIntentDetector', 'detect_intent_ir', 1, 1, 2).
python_method('KeywordIntentDetector', 'detect_all', 1, 8, 9).
python_method('KeywordIntentDetector', '_match_keyword', 2, 1, 1).
python_method('KeywordIntentDetector', '_fast_path_detection', 2, 73, 12).
python_method('KeywordIntentDetector', '_fuzzy_detection', 1, 6, 4).
python_method('KeywordIntentDetector', '_ml_detection', 1, 6, 4).
python_method('KeywordIntentDetector', '_semantic_detection', 1, 6, 4).
python_method('KeywordIntentDetector', '_keyword_detection', 2, 15, 12).
python_method('KeywordIntentDetector', '_calculate_keyword_confidence', 2, 6, 5).
python_method('KeywordIntentDetector', '_tokenize_text', 1, 11, 10).
python_method('KeywordIntentDetector', '_keyword_matches', 3, 6, 7).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_patterns.py', 'KeywordPatterns').
python_method('KeywordPatterns', '__init__', 1, 3, 7).
python_method('KeywordPatterns', '_load_patterns_from_json', 1, 19, 14).
python_method('KeywordPatterns', '_load_detector_config_from_json', 0, 33, 13).
python_method('KeywordPatterns', 'get_domain_patterns', 1, 1, 1).
python_method('KeywordPatterns', 'get_intent_patterns', 2, 1, 1).
python_method('KeywordPatterns', 'has_domain', 1, 1, 0).
python_method('KeywordPatterns', 'has_intent', 2, 1, 1).
python_method('KeywordPatterns', 'list_domains', 0, 1, 2).
python_method('KeywordPatterns', 'list_intents', 1, 1, 3).
python_method('KeywordPatterns', 'add_pattern', 3, 6, 5).
python_method('KeywordPatterns', 'get_domain_boosters', 1, 1, 1).
python_method('KeywordPatterns', 'get_priority_intents', 1, 1, 1).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/normalize.py', 'QueryNormalizer').
python_method('QueryNormalizer', 'normalize', 1, 2, 2).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/protocols.py', 'IntentDetector').
python_method('IntentDetector', 'detect', 1, 1, 0).
python_class('packages/nlp2cmd-intent/src/nlp2cmd_intent/protocols.py', 'EntityExtractor').
python_method('EntityExtractor', 'extract', 1, 1, 0).
python_class('packages/nlp2cmd-intent/tests/test_nlp2cmd_convert.py', 'FakeDetection').
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/pipeline.py', 'PlanningPipeline').
python_method('PlanningPipeline', '__init__', 0, 3, 2).
python_method('PlanningPipeline', 'run', 1, 1, 3).
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/router.py', 'UnsupportedIntentError').
python_method('UnsupportedIntentError', '__init__', 1, 2, 2).
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/router.py', 'PlanRouter').
python_method('PlanRouter', '__init__', 1, 2, 2).
python_method('PlanRouter', 'select', 1, 3, 2).
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rest_workflow.py', 'RestWorkflowPlanStrategy').
python_method('RestWorkflowPlanStrategy', 'supports', 1, 4, 1).
python_method('RestWorkflowPlanStrategy', 'plan', 1, 7, 6).
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategies/rule_shell.py', 'RuleShellPlanStrategy').
python_method('RuleShellPlanStrategy', 'supports', 1, 2, 0).
python_method('RuleShellPlanStrategy', 'plan', 1, 3, 5).
python_class('packages/nlp2cmd-planner/src/nlp2cmd_planner/strategy.py', 'PlanStrategy').
python_method('PlanStrategy', 'supports', 1, 1, 0).
python_method('PlanStrategy', 'plan', 1, 1, 0).
python_class('packages/nlp2cmd-propact/src/nlp2cmd_propact/executor.py', 'HybridPlanExecutor').
python_method('HybridPlanExecutor', '__init__', 0, 2, 1).
python_method('HybridPlanExecutor', 'run', 1, 10, 8).
python_method('HybridPlanExecutor', '_run_propact_step', 2, 1, 2).
python_method('HybridPlanExecutor', '_run_nlp2cmd_step', 2, 5, 7).
python_class('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', 'RunResult').
python_class('packages/nlp2cmd-propact/src/nlp2cmd_propact/runner.py', 'PropactRunner').
python_method('PropactRunner', '__init__', 0, 1, 0).
python_method('PropactRunner', 'render', 1, 1, 1).
python_method('PropactRunner', 'run', 1, 8, 9).
python_method('PropactRunner', '_run_via_propact', 2, 2, 6).
python_class('packages/pact-ir/src/pact_ir/execution_plan.py', 'PlanStep').
python_class('packages/pact-ir/src/pact_ir/execution_plan.py', 'ExecutionPlanIR').
python_method('ExecutionPlanIR', 'from_intent', 2, 1, 1).
python_method('ExecutionPlanIR', 'primary_target_kind', 0, 2, 0).
python_method('ExecutionPlanIR', 'step_count', 0, 1, 1).
python_class('packages/pact-ir/src/pact_ir/intent.py', 'Ambiguity').
python_class('packages/pact-ir/src/pact_ir/intent.py', 'EntityBag').
python_method('EntityBag', 'get', 2, 1, 1).
python_class('packages/pact-ir/src/pact_ir/intent.py', 'IntentIR').
python_method('IntentIR', 'needs_clarification', 0, 2, 1).
python_class('packages/pact-ir/src/pact_ir/target_kind.py', 'TargetKind').
python_method('TargetKind', 'propact_protocol', 0, 1, 1).
python_class('packages/pact-ir/src/pact_ir/target_kind.py', 'ExecutionRisk').
python_class('scripts/run-example-testql-results.py', 'Check').
python_class('scripts/run-example-testql-results.py', 'ExampleReport').
python_method('ExampleReport', 'failures', 0, 3, 1).
python_method('ExampleReport', 'to_dict', 0, 6, 4).
python_class('tests/test_nlp2dsl_sdk.py', 'DummyResponse').
python_method('DummyResponse', '__init__', 2, 1, 1).
python_method('DummyResponse', 'raise_for_status', 0, 2, 1).
python_method('DummyResponse', 'json', 0, 1, 0).
python_class('tests/test_nlp2dsl_sdk.py', 'DummySession').
python_method('DummySession', '__init__', 1, 1, 1).
python_method('DummySession', 'request', 2, 2, 3).
python_method('DummySession', 'close', 0, 1, 0).
python_class('worker/config.py', 'WorkerSettings').
python_class('worker/logging_setup.py', 'JSONFormatter').
python_method('JSONFormatter', '__init__', 1, 1, 2).
python_method('JSONFormatter', 'format', 1, 2, 6).
python_class('worker/logging_setup.py', 'RequestIDMiddleware').
python_method('RequestIDMiddleware', '__init__', 2, 1, 2).
python_method('RequestIDMiddleware', 'dispatch', 2, 2, 5).
python_class('worker/tests/test_worker.py', 'TestWorkerHealth').
python_method('TestWorkerHealth', 'test_health', 1, 6, 3).
python_class('worker/tests/test_worker.py', 'TestExecuteActions').
python_method('TestExecuteActions', 'test_execute_send_invoice', 1, 5, 2).
python_method('TestExecuteActions', 'test_execute_send_email', 1, 4, 2).
python_method('TestExecuteActions', 'test_execute_generate_report', 1, 4, 2).
python_method('TestExecuteActions', 'test_execute_notify_slack', 1, 4, 2).
python_method('TestExecuteActions', 'test_execute_notify_telegram', 1, 4, 2).
python_method('TestExecuteActions', 'test_execute_notify_teams', 1, 4, 2).
python_method('TestExecuteActions', 'test_execute_unknown_action', 1, 3, 2).
python_class('worker/tests/test_worker.py', 'TestActionRegistry').
python_method('TestActionRegistry', 'test_handlers_registered', 0, 2, 1).
python_method('TestActionRegistry', 'test_all_handlers_callable', 0, 3, 2).

% ── Dependencies ─────────────────────────────────────────

% ── Makefile Targets ─────────────────────────────────────
makefile_target('PACKAGES', '').
makefile_target('GREEN', '').
makefile_target('YELLOW', '').
makefile_target('BLUE', '').
makefile_target('NC', '').
makefile_target('help', '').
makefile_target('install', '').
makefile_target('install-dev', '').
makefile_target('setup-dev', '').
makefile_target('update', '').
makefile_target('test', '').
makefile_target('check-pypi-deps', '').
makefile_target('clean', '').
makefile_target('build', '').
makefile_target('build-packages', '').
makefile_target('build-all', '').
makefile_target('publish-root', '').
makefile_target('publish-packages', '').
makefile_target('publish-package', '').
makefile_target('publish', '').
makefile_target('version', '').
makefile_target('package-versions', '').

% ── Taskfile Tasks ───────────────────────────────────────

% ── Environment Variables ────────────────────────────────
env_variable('OPENROUTER_API_KEY', '*(not set)*', '── OpenRouter (domyślny) ────────────────────────────────────').
env_variable('LLM_MODEL', 'openrouter/openai/gpt-5-mini', 'NLP_ENRICH_MISSING=1').
env_variable('LLM_TEMPERATURE', '0', '── LLM Settings ─────────────────────────────────────────────').
env_variable('LLM_MAX_TOKENS', '1024', '').
env_variable('LLM_FALLBACK_THRESHOLD', '0.5', '').
env_variable('NLP2DSL_BACKEND_HOST_PORT', '8010', '8002 jest zajęty przez Mullm Projector, gdy oba stacki działają równolegle.').
env_variable('NLP2DSL_NLP_HOST_PORT', '8012', '').
env_variable('NLP2DSL_WORKER_HOST_PORT', '8004', '').
env_variable('NLP2DSL_CONFIG', './nlp2dsl.yaml', '').
env_variable('NLP2DSL_AGENT_ID', 'user', '').
env_variable('DEEPGRAM_API_KEY', '*(not set)*', 'Zdobądź klucz: https://console.deepgram.com/').

% ── TestQL Scenarios ─────────────────────────────────────
testql_scenario('generated-api-smoke.testql.toon.yaml', 'api').
testql_scenario('generated-cli-tests.testql.toon.yaml', 'cli').
testql_scenario('generated-examples.testql.toon.yaml', 'cli').
testql_scenario('generated-from-pytests.testql.toon.yaml', 'integration').

% ── Semantic Facts from SUMD.md ──────────────────────────
sumd_declared_file('app.doql.less', 'doql').
sumd_declared_file('testql-scenarios/generated-api-smoke.testql.toon.yaml', 'testql').
sumd_declared_file('testql-scenarios/generated-cli-tests.testql.toon.yaml', 'testql').
sumd_declared_file('testql-scenarios/generated-examples.testql.toon.yaml', 'testql').
sumd_declared_file('testql-scenarios/generated-from-pytests.testql.toon.yaml', 'testql').
sumd_declared_file('pyqual.yaml', 'pyqual').
sumd_declared_file('project/map.toon.yaml', 'analysis').
sumd_declared_file('project/logic.pl', 'analysis').
sumd_declared_file('project/calls.toon.yaml', 'analysis').
sumd_interface('api', '').
sumd_interface('cli', 'argparse').
sumd_interface('cli', '').
sumd_workflow('install', 'manual').
sumd_workflow_step('install', 1, '$(PYTHON) -m pip install -e .').
sumd_workflow('install-dev', 'manual').
sumd_workflow('setup-dev', 'manual').
sumd_workflow_step('setup-dev', 1, './scripts/setup-dev.sh').
sumd_workflow('update', 'manual').
sumd_workflow_step('update', 1, 'echo "$(YELLOW)==> update integration stack$(NC)"').
sumd_workflow_step('update', 2, './scripts/setup-dev.sh').
sumd_workflow('test', 'manual').
sumd_workflow_step('test', 1, '$(PYTHON) -m pytest tests/ -v').
sumd_workflow('check-pypi-deps', 'manual').
sumd_workflow_step('check-pypi-deps', 1, '$(PYTHON) -c "import build, twine" 2>/dev/null || $(PYTHON) -m pip install build twine -q').
sumd_workflow('clean', 'manual').
sumd_workflow_step('clean', 1, 'rm -rf dist/ build/ *.egg-info').
sumd_workflow_step('clean', 2, 'for pkg in $(PACKAGES)').
sumd_workflow_step('clean', 3, 'rm -rf $$pkg/dist $$pkg/build $$pkg/src/*.egg-info 2>/dev/null || true').
sumd_workflow_step('clean', 4, 'done').
sumd_workflow('build', 'manual').
sumd_workflow_step('build', 1, 'echo "$(YELLOW)==> build root SDK$(NC)"').
sumd_workflow_step('build', 2, '$(PYTHON) -m build .').
sumd_workflow('build-packages', 'manual').
sumd_workflow_step('build-packages', 1, 'for pkg in $(PACKAGES)').
sumd_workflow_step('build-packages', 2, 'echo "$(YELLOW)==> build $$pkg$(NC)"').
sumd_workflow_step('build-packages', 3, '$(PYTHON) -m build $$pkg').
sumd_workflow_step('build-packages', 4, 'done').
sumd_workflow('build-all', 'manual').
sumd_workflow('publish-root', 'manual').
sumd_workflow_step('publish-root', 1, 'echo "$(YELLOW)==> twine upload root SDK$(NC)"').
sumd_workflow_step('publish-root', 2, '$(PYTHON) -m twine upload dist/*').
sumd_workflow('publish-packages', 'manual').
sumd_workflow_step('publish-packages', 1, 'for pkg in $(PACKAGES)').
sumd_workflow_step('publish-packages', 2, 'echo "$(YELLOW)==> twine upload $$pkg$(NC)"').
sumd_workflow_step('publish-packages', 3, '$(PYTHON) -m twine upload --skip-existing $$pkg/dist/* || exit 1').
sumd_workflow_step('publish-packages', 4, 'sleep $(PYPI_UPLOAD_DELAY)').
sumd_workflow_step('publish-packages', 5, 'done').
sumd_workflow('publish-package', 'manual').
sumd_workflow_step('publish-package', 1, 'test -n "$(PKG)" || (echo "Usage: make publish-package PKG=packages/nlp2dsl-show" && exit 1)').
sumd_workflow_step('publish-package', 2, 'echo "$(YELLOW)==> build $(PKG)$(NC)"').
sumd_workflow_step('publish-package', 3, '$(PYTHON) -m build $(PKG)').
sumd_workflow_step('publish-package', 4, 'echo "$(YELLOW)==> twine upload $(PKG)$(NC)"').
sumd_workflow_step('publish-package', 5, '$(PYTHON) -m twine upload --skip-existing $(PKG)/dist/*').
sumd_workflow('publish', 'manual').
sumd_workflow_step('publish', 1, 'echo "$(YELLOW)==> Publishing nlp2dsl + packages to PyPI$(NC)"').
sumd_workflow_step('publish', 2, '$(PYTHON) -m twine upload dist/*').
sumd_workflow_step('publish', 3, 'for pkg in $(PACKAGES)').
sumd_workflow_step('publish', 4, 'echo "$(YELLOW)==> twine upload $$pkg$(NC)"').
sumd_workflow_step('publish', 5, '$(PYTHON) -m twine upload $$pkg/dist/*').
sumd_workflow_step('publish', 6, 'done').
sumd_workflow_step('publish', 7, 'echo "$(GREEN)Done: nlp2dsl + $(words $(PACKAGES)) packages published$(NC)"').
sumd_workflow('version', 'manual').
sumd_workflow_step('version', 1, 'grep -m1 \'^version = \' pyproject.toml | cut -d\'"\' -f2').
sumd_workflow('package-versions', 'manual').
sumd_workflow_step('package-versions', 1, 'for pkg in $(PACKAGES)').
sumd_workflow_step('package-versions', 2, 'v=$$(grep -m1 \'^version = \' $$pkg/pyproject.toml | cut -d\'"\' -f2)').
sumd_workflow_step('package-versions', 3, 'echo "$$pkg: $$v"').
sumd_workflow_step('package-versions', 4, 'done').
sumd_deploy_target('docker_compose').
sumd_deploy_compose_file('docker-compose.yml').
```

## Call Graph

*342 nodes · 350 edges · 72 modules · CC̄=3.6*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `_load_detector_config_from_json` *(in packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns)* | 33 ⚠ | 0 | 48 | **48** |
| `_execute_workflow` *(in backend.app.engine)* | 11 ⚠ | 2 | 42 | **44** |
| `print_workflow_preview` *(in nlp2dsl_sdk.preview)* | 11 ⚠ | 8 | 27 | **35** |
| `resolve_intent` *(in nlp-service.app.routing.resolve)* | 18 ⚠ | 1 | 31 | **32** |
| `_run` *(in nlp2dsl_sdk.cli)* | 12 ⚠ | 1 | 30 | **31** |
| `enrich_entities` *(in nlp-service.app.routing.parser.enrich)* | 14 ⚠ | 1 | 29 | **30** |
| `build_process_trace` *(in nlp2dsl_sdk.artifacts)* | 17 ⚠ | 1 | 29 | **30** |
| `_build_config` *(in nlp-service.app.dsl.mapper)* | 19 ⚠ | 1 | 29 | **30** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/wronai/nlp2dsl
# generated in 0.27s
# nodes: 342 | edges: 350 | modules: 72
# CC̄=3.6

HUBS[20]:
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_detector_config_from_json
    CC=33  in:0  out:48  total:48
  backend.app.engine._execute_workflow
    CC=11  in:2  out:42  total:44
  nlp2dsl_sdk.preview.print_workflow_preview
    CC=11  in:8  out:27  total:35
  nlp-service.app.routing.resolve.resolve_intent
    CC=18  in:1  out:31  total:32
  nlp2dsl_sdk.cli._run
    CC=12  in:1  out:30  total:31
  nlp-service.app.routing.parser.enrich.enrich_entities
    CC=14  in:1  out:29  total:30
  nlp2dsl_sdk.artifacts.build_process_trace
    CC=17  in:1  out:29  total:30
  nlp-service.app.dsl.mapper._build_config
    CC=19  in:1  out:29  total:30
  nlp-service.app.routing.orientation.orient_query
    CC=16  in:2  out:27  total:29
  nlp2dsl_sdk.cli._display
    CC=13  in:1  out:27  total:28
  nlp-service.app.governance.bootstrap._actions_from_yaml_areas
    CC=14  in:1  out:26  total:27
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_patterns_from_json
    CC=19  in:0  out:26  total:26
  examples.08-multi-object-benchmark.scenario.run_benchmark
    CC=16  in:2  out:24  total:26
  examples.12-ir-show.scenario.run
    CC=13  in:0  out:25  total:25
  nlp-service.app.routing.orientation._resolve_file_list_host_command
    CC=15  in:1  out:24  total:25
  nlp2dsl_sdk.cli.main
    CC=7  in:0  out:25  total:25
  packages.nlp2cmd-intent.src.nlp2cmd_intent.nlp2cmd_convert.detection_to_intent_ir
    CC=10  in:2  out:22  total:24
  nlp-service.app.main.websocket_chat
    CC=10  in:0  out:23  total:23
  nlp-service.app.settings.SettingsManager.set
    CC=4  in:12  out:11  total:23
  backend.app.routers.workflow.stream_workflow
    CC=2  in:0  out:22  total:22

MODULES:
  backend.app.engine  [7 funcs]
    _execute_workflow  CC=11  out:42
    _persist_workflow_snapshot  CC=2  out:2
    _publish_workflow_event  CC=2  out:2
    _track_background_task  CC=1  out:5
    _workflow_steps_payload  CC=2  out:1
    run_workflow  CC=1  out:2
    start_workflow  CC=1  out:7
  backend.app.logging_setup  [1 funcs]
    get_request_id  CC=1  out:1
  backend.app.routers.chat  [4 funcs]
    _proxy_chat_payload  CC=9  out:16
    chat_get_state  CC=2  out:7
    chat_message  CC=12  out:21
    chat_start  CC=2  out:4
  backend.app.routers.settings  [7 funcs]
    action_schema  CC=2  out:6
    actions_schema  CC=1  out:5
    get_settings  CC=1  out:5
    get_settings_section  CC=2  out:6
    reset_settings  CC=1  out:5
    set_setting  CC=2  out:6
    update_settings_section  CC=2  out:6
  backend.app.routers.system  [1 funcs]
    system_execute  CC=2  out:6
  backend.app.routers.workflow  [5 funcs]
    _format_sse  CC=5  out:6
    _workflow_snapshot  CC=1  out:7
    run_workflow_endpoint  CC=1  out:2
    start_workflow_endpoint  CC=1  out:2
    stream_workflow  CC=2  out:22
  backend.app.workflow_events  [2 funcs]
    publish  CC=2  out:4
    subscriber_count  CC=1  out:3
  examples.01-invoice.scenario  [1 funcs]
    run  CC=7  out:22
  examples.02-email.scenario  [1 funcs]
    run  CC=7  out:19
  examples.03-report-and-notify.scenario  [1 funcs]
    run  CC=6  out:16
  examples.04-scheduled-report.scenario  [1 funcs]
    run  CC=11  out:21
  examples.05-conversation-flow.scenario  [3 funcs]
    run  CC=2  out:2
    run_demo  CC=2  out:15
    run_interactive  CC=1  out:2
  examples.06-interactive-chat.scenario  [3 funcs]
    run  CC=2  out:2
    run_demo  CC=3  out:9
    run_interactive  CC=1  out:4
  examples.07-email-conversation.scenario  [1 funcs]
    run  CC=3  out:11
  examples.08-multi-object-benchmark.scenario  [4 funcs]
    _evaluate  CC=6  out:9
    _extract_actions  CC=5  out:5
    run  CC=5  out:15
    run_benchmark  CC=16  out:24
  examples.09-execution-smoke.scenario  [1 funcs]
    run  CC=9  out:22
  examples.10-llm-benchmark.scenario  [1 funcs]
    run  CC=3  out:10
  examples.11-notify-quality.scenario  [1 funcs]
    run  CC=8  out:17
  examples.12-ir-show.scenario  [1 funcs]
    run  CC=13  out:25
  examples.bootstrap  [1 funcs]
    bootstrap  CC=3  out:4
  examples.code_generation_examples  [1 funcs]
    main  CC=1  out:1
  nlp-service.app.access.uri_match  [3 funcs]
    normalize_uri  CC=2  out:1
    scheme_allowed  CC=5  out:2
    uri_matches  CC=8  out:11
  nlp-service.app.audio_parser  [4 funcs]
    send_audio  CC=2  out:2
    is_stt_available  CC=2  out:0
    stt_audio  CC=9  out:14
    stt_file  CC=2  out:4
  nlp-service.app.conversation.merge  [1 funcs]
    merge_into_state  CC=13  out:4
  nlp-service.app.conversation.orchestrator  [5 funcs]
    _attach_routing  CC=1  out:1
    _process_message  CC=6  out:16
    continue_conversation  CC=2  out:8
    get_conversation  CC=2  out:2
    start_conversation  CC=1  out:6
  nlp-service.app.conversation.responses  [10 funcs]
    _execute_keyword_in_text  CC=3  out:4
    _is_execute_or_continue  CC=2  out:4
    _nlp_from_state  CC=5  out:5
    build_and_check_dsl  CC=4  out:6
    build_incomplete_response  CC=3  out:6
    check_execute_keyword  CC=7  out:5
    deny_message  CC=3  out:0
    format_system_result  CC=3  out:6
    handle_system_action  CC=7  out:7
    handle_unknown_intent  CC=5  out:6
  nlp-service.app.dsl.forms  [1 funcs]
    get_action_form  CC=5  out:12
  nlp-service.app.dsl.mapper  [5 funcs]
    _build_config  CC=19  out:29
    _get_field_mapping  CC=1  out:1
    _make_name  CC=3  out:2
    _resolve_actions  CC=7  out:4
    map_to_dsl  CC=8  out:17
  nlp-service.app.dsl.pipeline  [1 funcs]
    map_to_dsl_with_enrichment  CC=6  out:4
  nlp-service.app.execution.delegate  [2 funcs]
    execution_backend_for_intent  CC=2  out:1
    is_delegated_to_mullm  CC=2  out:1
  nlp-service.app.governance.bootstrap  [3 funcs]
    _actions_from_yaml_areas  CC=14  out:26
    apply_yaml_actions  CC=4  out:6
    bootstrap_registry  CC=1  out:7
  nlp-service.app.governance.config  [11 funcs]
    _allowed_uri_schemes  CC=3  out:2
    _build_access_config  CC=7  out:18
    _default_agent  CC=3  out:3
    _enabled_integrations  CC=7  out:5
    _load_merged_config  CC=4  out:7
    _load_yaml_file  CC=3  out:4
    _merge_dict  CC=8  out:6
    _search_paths  CC=6  out:17
    get_access_config  CC=1  out:1
    load_access_config  CC=3  out:2
  nlp-service.app.governance.policy  [13 funcs]
    _action_context  CC=5  out:5
    _area_selector_match  CC=3  out:0
    _decision  CC=1  out:1
    _effect_decision  CC=4  out:4
    _grant_action_matches  CC=4  out:4
    _grant_matches  CC=2  out:2
    _grant_target_matches  CC=5  out:6
    _matched_effect  CC=3  out:4
    _scheme_decision  CC=3  out:2
    _unknown_agent_decision  CC=4  out:3
  nlp-service.app.main  [15 funcs]
    _run_parser  CC=3  out:3
    access_check  CC=3  out:6
    access_config  CC=3  out:12
    access_reload  CC=2  out:2
    action_schema  CC=2  out:3
    actions_schema  CC=3  out:3
    chat_message  CC=5  out:13
    chat_start  CC=5  out:12
    chat_state  CC=2  out:4
    health  CC=3  out:8
  nlp-service.app.registry  [4 funcs]
    get_defaults  CC=1  out:3
    get_quality_required_fields  CC=1  out:3
    get_required_fields  CC=1  out:2
    get_trigger  CC=3  out:2
  nlp-service.app.routing.native  [13 funcs]
    _aliases_match  CC=2  out:3
    _best_action_alias  CC=3  out:3
    _best_alias_for_action  CC=6  out:5
    _keywords_pattern_matches  CC=4  out:5
    _match_route  CC=4  out:6
    _pattern_matches  CC=4  out:5
    _patterns_match  CC=3  out:3
    _regex_pattern_matches  CC=4  out:4
    _resolve_action_alias  CC=2  out:6
    _resolve_configured_route  CC=5  out:5
  nlp-service.app.routing.observability  [2 funcs]
    record_intent_decision  CC=7  out:4
    routing_metrics_snapshot  CC=1  out:1
  nlp-service.app.routing.orientation  [4 funcs]
    _host_list_root  CC=3  out:2
    _is_file_list_query  CC=5  out:8
    _resolve_file_list_host_command  CC=15  out:24
    orient_query  CC=16  out:27
  nlp-service.app.routing.parser.enrich  [4 funcs]
    can_enrich_missing  CC=4  out:5
    enrich_entities  CC=14  out:29
    get_enrichable_missing  CC=5  out:3
    is_enrich_enabled  CC=1  out:3
  nlp-service.app.routing.parser.facade  [1 funcs]
    parse_text  CC=2  out:4
  nlp-service.app.routing.parser.llm  [3 funcs]
    _detect_provider  CC=10  out:8
    _parse_json_response  CC=6  out:10
    parse_llm  CC=3  out:16
  nlp-service.app.routing.parser.resolve_mode  [1 funcs]
    parse_with_mode  CC=10  out:12
  nlp-service.app.routing.parser.rules  [30 funcs]
    _action_alias_scores  CC=4  out:3
    _action_category  CC=1  out:2
    _actions_by_score  CC=1  out:2
    _alias_in_text  CC=3  out:4
    _apply_context_filters  CC=21  out:17
    _detect_actions  CC=6  out:6
    _dominant_overlap_action  CC=4  out:5
    _extract_amount  CC=5  out:7
    _extract_body_content_prefix  CC=4  out:4
    _extract_email  CC=3  out:2
  nlp-service.app.routing.resolve  [4 funcs]
    _intent_from_nlp  CC=2  out:7
    _intent_from_orientation  CC=4  out:9
    _parser_source  CC=5  out:4
    resolve_intent  CC=18  out:31
  nlp-service.app.settings  [2 funcs]
    set  CC=4  out:11
    _coerce_type  CC=5  out:6
  nlp-service.app.store.factory  [1 funcs]
    get_conversation_store  CC=4  out:7
  nlp-service.app.system_executor  [5 funcs]
    _exec_file_read  CC=9  out:18
    _exec_file_write  CC=4  out:12
    _is_read_only  CC=2  out:5
    _validate_file_path  CC=5  out:9
    execute_system_action  CC=3  out:5
  nlp-service.integrations.loader  [3 funcs]
    _integration_names  CC=5  out:6
    apply_integrations  CC=5  out:7
    load_integration_registries  CC=5  out:10
  nlp2dsl_sdk.__main__  [1 funcs]
    main  CC=5  out:10
  nlp2dsl_sdk.artifacts  [15 funcs]
    __init__  CC=5  out:6
    finalize  CC=4  out:6
    record  CC=1  out:6
    _extract_actions  CC=4  out:5
    _mask_secret  CC=3  out:1
    _slugify  CC=2  out:5
    build_process_trace  CC=17  out:29
    collect_environment  CC=6  out:4
    example_artifact_root  CC=1  out:2
    get_example_writer  CC=2  out:4
  nlp2dsl_sdk.cli  [10 funcs]
    _actions  CC=3  out:8
    _analyze  CC=2  out:1
    _chat_start  CC=2  out:10
    _client  CC=1  out:1
    _demo  CC=6  out:5
    _display  CC=13  out:27
    _health  CC=2  out:6
    _run  CC=12  out:30
    main  CC=7  out:25
    show  CC=2  out:3
  nlp2dsl_sdk.client  [8 funcs]
    crm_update  CC=2  out:3
    generate_report  CC=1  out:2
    generate_report_and_notify  CC=4  out:6
    notify_slack  CC=2  out:2
    send_email  CC=3  out:2
    send_invoice  CC=1  out:2
    send_invoice_and_notify  CC=4  out:6
    workflow_step  CC=1  out:1
  nlp2dsl_sdk.demos  [10 funcs]
    _get_supported_languages  CC=3  out:6
    _print_code_generation_preview  CC=3  out:11
    _run_conversation_code_example  CC=3  out:14
    _run_direct_code_generation  CC=5  out:9
    _run_workflow_code_examples  CC=1  out:1
    list_available_demos  CC=1  out:0
    run_action_catalog_demo  CC=6  out:16
    run_automation_gallery_demo  CC=4  out:6
    run_code_generation_demo  CC=6  out:14
    run_crm_update_demo  CC=3  out:5
  nlp2dsl_sdk.encoding  [7 funcs]
    _apply_utf8_locale_env  CC=2  out:3
    _auto_configure_once  CC=2  out:1
    _explicit_utf8_locale  CC=4  out:2
    _reconfigure_stdio  CC=4  out:2
    _set_utf8_locale  CC=3  out:1
    configure_utf8  CC=3  out:4
    utf8_auto_enabled  CC=1  out:3
  nlp2dsl_sdk.preview  [9 funcs]
    ensure_services  CC=2  out:2
    execute_from_text  CC=8  out:15
    execute_text_examples  CC=8  out:9
    finalize_example_artifacts  CC=2  out:2
    preview_text_examples  CC=9  out:13
    print_execution_result  CC=5  out:11
    print_json  CC=1  out:2
    print_workflow_preview  CC=11  out:27
    workflow_http_error_result  CC=11  out:13
  packages.nlp2cmd-intent.src.nlp2cmd_intent.clarification  [2 funcs]
    clarification_enforced  CC=1  out:3
    ensure_intent_clear  CC=4  out:3
  packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files  [3 funcs]
    _nlp2cmd_data_dir  CC=2  out:3
    _package_data_dir  CC=2  out:5
    find_data_files  CC=6  out:17
  packages.nlp2cmd-intent.src.nlp2cmd_intent.facade  [3 funcs]
    __init__  CC=4  out:3
    detect  CC=2  out:4
    default_intent_detector  CC=1  out:1
  packages.nlp2cmd-intent.src.nlp2cmd_intent.input  [1 funcs]
    analyze_query  CC=3  out:8
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_detector  [14 funcs]
    _calculate_keyword_confidence  CC=6  out:5
    _fuzzy_detection  CC=6  out:4
    _ml_detection  CC=6  out:4
    _semantic_detection  CC=6  out:4
    _tokenize_text  CC=11  out:15
    detect  CC=17  out:21
    detect_all  CC=8  out:10
    detect_intent_ir  CC=1  out:2
    _get_fuzzy_schema_matcher  CC=7  out:7
    _get_ml_classifier  CC=8  out:6
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns  [7 funcs]
    __init__  CC=3  out:7
    _load_detector_config_from_json  CC=33  out:48
    _load_patterns_from_json  CC=19  out:26
    add_pattern  CC=6  out:6
    _dedupe_case_insensitive  CC=3  out:4
    _find_data_files  CC=1  out:2
    _normalize_polish_text  CC=1  out:2
  packages.nlp2cmd-intent.src.nlp2cmd_intent.nlp2cmd_convert  [1 funcs]
    detection_to_intent_ir  CC=10  out:22
  packages.nlp2cmd-planner.src.nlp2cmd_planner.strategies.rest_workflow  [2 funcs]
    plan  CC=7  out:14
    supports  CC=4  out:1
  packages.nlp2cmd-planner.src.nlp2cmd_planner.strategies.rule_shell  [2 funcs]
    plan  CC=3  out:6
    _parse_file_search  CC=10  out:11
  packages.nlp2cmd-planner.src.nlp2cmd_planner.workflow_backend  [4 funcs]
    fetch_workflow_from_text  CC=4  out:12
    workflow_backend_enabled  CC=1  out:3
    workflow_backend_url  CC=1  out:4
    workflow_run_path  CC=2  out:2
  packages.nlp2cmd-propact.src.nlp2cmd_propact.adapter  [8 funcs]
    _delegate_block  CC=4  out:4
    _format_json_body  CC=2  out:3
    _mcp_block  CC=6  out:13
    _rest_block  CC=2  out:5
    _shell_block  CC=1  out:1
    _ws_block  CC=5  out:11
    plan_to_propact_markdown  CC=2  out:4
    step_to_propact_block  CC=12  out:17
  packages.nlp2cmd-propact.src.nlp2cmd_propact.executor  [5 funcs]
    _run_nlp2cmd_step  CC=5  out:13
    _run_propact_step  CC=1  out:2
    run  CC=10  out:20
    _single_step_plan  CC=1  out:2
    execution_route  CC=3  out:0
  packages.nlp2cmd-propact.src.nlp2cmd_propact.runner  [8 funcs]
    render  CC=1  out:1
    run  CC=8  out:14
    _is_shell_only  CC=3  out:2
    _propact_available  CC=1  out:2
    _requires_propact  CC=2  out:1
    _resolve_propact_bin  CC=2  out:2
    _run_shell_steps  CC=7  out:19
    _shell_command  CC=3  out:3
  packages.nlp2dsl-show.src.nlp2dsl_show.cli  [1 funcs]
    main  CC=7  out:17
  tauri-wrapper.scripts.dev  [3 funcs]
    exitCode  CC=2  out:1
    main  CC=11  out:10
    shutdown  CC=5  out:5
  tauri-wrapper.scripts.serve-dist  [9 funcs]
    contentType  CC=2  out:3
    fileContents  CC=1  out:2
    handleRequest  CC=6  out:6
    isInsideRoot  CC=3  out:3
    resolveRequestPath  CC=8  out:8
    sendFile  CC=1  out:4
    server  CC=4  out:5
    startServer  CC=4  out:10
    stat  CC=2  out:2
  worker.worker  [10 funcs]
    _deliver_notification  CC=5  out:16
    action  CC=1  out:0
    handle_crm_update  CC=1  out:5
    handle_generate_code  CC=5  out:17
    handle_generate_report  CC=1  out:9
    handle_notify_slack  CC=1  out:5
    handle_notify_teams  CC=1  out:6
    handle_notify_telegram  CC=1  out:5
    handle_send_email  CC=1  out:8
    handle_send_invoice  CC=1  out:9

EDGES:
  tauri-wrapper.scripts.dev.main → tauri-wrapper.scripts.dev.shutdown
  tauri-wrapper.scripts.dev.exitCode → tauri-wrapper.scripts.dev.main
  tauri-wrapper.scripts.serve-dist.resolveRequestPath → tauri-wrapper.scripts.serve-dist.isInsideRoot
  tauri-wrapper.scripts.serve-dist.resolveRequestPath → tauri-wrapper.scripts.serve-dist.stat
  tauri-wrapper.scripts.serve-dist.sendFile → tauri-wrapper.scripts.serve-dist.contentType
  tauri-wrapper.scripts.serve-dist.fileContents → tauri-wrapper.scripts.serve-dist.contentType
  tauri-wrapper.scripts.serve-dist.handleRequest → tauri-wrapper.scripts.serve-dist.resolveRequestPath
  tauri-wrapper.scripts.serve-dist.handleRequest → tauri-wrapper.scripts.serve-dist.contentType
  tauri-wrapper.scripts.serve-dist.handleRequest → tauri-wrapper.scripts.serve-dist.sendFile
  tauri-wrapper.scripts.serve-dist.startServer → tauri-wrapper.scripts.serve-dist.handleRequest
  tauri-wrapper.scripts.serve-dist.server → tauri-wrapper.scripts.serve-dist.handleRequest
  backend.app.engine._persist_workflow_snapshot → backend.app.engine._workflow_steps_payload
  backend.app.engine._execute_workflow → backend.app.engine._publish_workflow_event
  backend.app.engine._execute_workflow → backend.app.logging_setup.get_request_id
  backend.app.engine._execute_workflow → backend.app.engine._persist_workflow_snapshot
  backend.app.engine.run_workflow → backend.app.engine._execute_workflow
  backend.app.engine.start_workflow → backend.app.engine._track_background_task
  backend.app.engine.start_workflow → backend.app.engine._persist_workflow_snapshot
  backend.app.engine.start_workflow → backend.app.engine._execute_workflow
  backend.app.workflow_events.WorkflowEventHub.publish → nlp-service.app.settings.SettingsManager.set
  backend.app.workflow_events.WorkflowEventHub.subscriber_count → nlp-service.app.settings.SettingsManager.set
  backend.app.routers.system.system_execute → backend.app.logging_setup.get_request_id
  backend.app.routers.chat.chat_start → backend.app.routers.chat._proxy_chat_payload
  backend.app.routers.chat.chat_message → backend.app.routers.chat._proxy_chat_payload
  backend.app.routers.chat.chat_get_state → backend.app.logging_setup.get_request_id
  backend.app.routers.workflow.run_workflow_endpoint → backend.app.engine.run_workflow
  backend.app.routers.workflow.start_workflow_endpoint → backend.app.engine.start_workflow
  backend.app.routers.workflow.stream_workflow → backend.app.routers.workflow._workflow_snapshot
  backend.app.routers.workflow.stream_workflow → backend.app.routers.workflow._format_sse
  backend.app.routers.settings.actions_schema → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.action_schema → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.get_settings → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.get_settings_section → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.update_settings_section → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.set_setting → backend.app.logging_setup.get_request_id
  backend.app.routers.settings.reset_settings → backend.app.logging_setup.get_request_id
  packages.nlp2cmd-intent.src.nlp2cmd_intent.clarification.ensure_intent_clear → packages.nlp2cmd-intent.src.nlp2cmd_intent.clarification.clarification_enforced
  packages.nlp2cmd-intent.src.nlp2cmd_intent.facade.KeywordIntentAdapter.detect → packages.nlp2cmd-intent.src.nlp2cmd_intent.nlp2cmd_convert.detection_to_intent_ir
  packages.nlp2cmd-intent.src.nlp2cmd_intent.facade.IntentPipeline.__init__ → packages.nlp2cmd-intent.src.nlp2cmd_intent.facade.default_intent_detector
  packages.nlp2cmd-intent.src.nlp2cmd_intent.input.analyze_query → packages.nlp2cmd-intent.src.nlp2cmd_intent.clarification.ensure_intent_clear
  packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files.find_data_files → nlp-service.app.settings.SettingsManager.set
  packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files.find_data_files → packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files._package_data_dir
  packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files.find_data_files → packages.nlp2cmd-intent.src.nlp2cmd_intent.data_files._nlp2cmd_data_dir
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns._dedupe_case_insensitive → nlp-service.app.settings.SettingsManager.set
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns.__init__ → nlp-service.app.settings.SettingsManager.set
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_patterns_from_json → packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns._find_data_files
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_detector_config_from_json → packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns._find_data_files
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns.add_pattern → packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns._normalize_polish_text
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns.add_pattern → packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns._dedupe_case_insensitive
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_detector.KeywordIntentDetector.detect → packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_detector._get_query_normalizer
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Api (1)

**`Auto-generated API Smoke Tests`**
- assert `_status < 500`
- assert `_status >= 200`
- detectors: FastAPIDetector, WebSocketDetector, ConfigEndpointDetector

### Cli (2)

**`CLI Command Tests`**

**`NLP2DSL Examples (aggregated)`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

Reusable Python SDK for the NLP2DSL platform
