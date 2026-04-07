# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/nlp2dsl
- **Primary Language**: python
- **Languages**: python: 47, shell: 9, rust: 1, javascript: 1
- **Analysis Mode**: static
- **Total Functions**: 250
- **Total Classes**: 45
- **Modules**: 58
- **Entry Points**: 196

## Architecture by Module

### nlp2dsl_sdk.client
- **Functions**: 47
- **Classes**: 2
- **File**: `client.py`

### nlp-service.app.main
- **Functions**: 20
- **File**: `main.py`

### nlp2dsl_sdk.demos
- **Functions**: 17
- **Classes**: 1
- **File**: `demos.py`

### nlp-service.app.system_executor
- **Functions**: 13
- **File**: `system_executor.py`

### backend.app.db.postgres
- **Functions**: 11
- **Classes**: 3
- **File**: `postgres.py`

### nlp-service.app.settings
- **Functions**: 11
- **Classes**: 6
- **File**: `settings.py`

### worker.worker
- **Functions**: 9
- **File**: `worker.py`

### tauri-wrapper.scripts.dev
- **Functions**: 8
- **File**: `dev.js`

### nlp-service.app.audio_parser
- **Functions**: 8
- **Classes**: 1
- **File**: `audio_parser.py`

### nlp-service.app.code_generator
- **Functions**: 8
- **Classes**: 1
- **File**: `code_generator.py`

### backend.app.routers.settings
- **Functions**: 7
- **File**: `settings.py`

### nlp-service.app.orchestrator
- **Functions**: 7
- **File**: `orchestrator.py`

### nlp-service.app.store.redis_store
- **Functions**: 7
- **Classes**: 1
- **File**: `redis_store.py`

### backend.app.db.memory
- **Functions**: 6
- **Classes**: 1
- **File**: `memory.py`

### backend.app.db
- **Functions**: 6
- **Classes**: 1
- **File**: `__init__.py`

### backend.app.logging_setup
- **Functions**: 6
- **Classes**: 2
- **File**: `logging_setup.py`

### nlp-service.app.logging_setup
- **Functions**: 6
- **Classes**: 2
- **File**: `logging_setup.py`

### nlp-service.app.mapper
- **Functions**: 6
- **File**: `mapper.py`

### worker.logging_setup
- **Functions**: 6
- **Classes**: 2
- **File**: `logging_setup.py`

### backend.app.routers.workflow
- **Functions**: 5
- **File**: `workflow.py`

## Key Entry Points

Main execution flows into the system:

### nlp2dsl_sdk.client.ConversationFlow._handle_response
- **Calls**: data.get, data.get, self.history.append, print, data.get, data.get, print, form.get

### backend.app.routers.workflow.workflow_from_text
> Pełny pipeline: tekst → NLP → DSL → (opcjonalne) wykonanie.

Body: {"text": "...", "mode": "auto|rules|llm", "execute": true|false}
- **Calls**: router.post, body.get, body.get, body.get, nlp_resp.json, text.strip, HTTPException, AsyncClient

### nlp-service.app.main.websocket_chat
> WebSocket endpoint dla voice chat w czasie rzeczywistym.

Flow:
1. Klient łączy się przez WebSocket
2. Wysyła audio chunks (binary)
3. Server streamuj
- **Calls**: app.websocket, log.info, websocket.accept, nlp-service.app.audio_parser.is_stt_available, StreamingSTT, log.info, log.info, log.exception

### nlp2dsl_sdk.demos.run_action_catalog_demo
- **Calls**: print, client.workflow_actions, print, NLP2DSLClient.from_env, nlp2dsl_sdk.demos._ensure_services, action.get, print, client.workflow_action_schema

### nlp-service.app.system_executor._exec_file_read
- **Calls**: config.get, nlp-service.app.system_executor._validate_file_path, None.read_text, config.get, config.get, None.exists, None.is_file, content.split

### backend.app.routers.chat.chat_message
> Kontynuuj konwersację — uzupełnij brakujące dane.

Body: {"conversation_id": "abc", "text": "klient@firma.pl"}
- **Calls**: router.post, resp.json, None.lower, backend.app.routers.chat._proxy_chat_payload, HTTPException, any, result.get, body.get

### nlp-service.app.system_executor._exec_file_list
- **Calls**: config.get, config.get, sorted, candidate.exists, Path, resolved.rglob, str, len

### worker.worker.handle_generate_code
- **Calls**: worker.worker.action, config.get, config.get, config.get, config.get, ValueError, httpx.AsyncClient, response.raise_for_status

### nlp-service.app.system_executor._exec_registry_edit
- **Calls**: config.get, config.get, changes.append, config.get, isinstance, changes.append, config.get, isinstance

### nlp2dsl_sdk.client.ConversationFlow.run_demo
- **Calls**: print, print, self.start, print, self.send_message, print, self.send_message, print

### nlp-service.app.code_generator.CodeGenerator.generate_code
> Generate code in the specified language.

Args:
    description: Natural language description of what to generate
    language: Target programming lan
- **Calls**: self._build_prompt, None.message.content.strip, list, litellm.acompletion, None.format, self._split_code_and_tests, log.exception, SUPPORTED_LANGUAGES.keys

### nlp-service.app.main.chat_message
> Kontynuuj rozmowę — uzupełnij brakujące dane.

Obsługuje:
- Tekst: Form field "text"
- Audio: UploadFile (STT via Deepgram)

Examples:
    # Tekst
   
- **Calls**: app.post, Form, Form, File, log.info, text.strip, HTTPException, nlp-service.app.orchestrator.continue_conversation

### nlp-service.app.system_executor._exec_file_write
- **Calls**: config.get, config.get, config.get, nlp-service.app.system_executor._validate_file_path, nlp-service.app.system_executor._is_read_only, Path, p.parent.mkdir, p.write_text

### nlp-service.app.system_executor._exec_registry_add
- **Calls**: config.get, config.get, config.get, isinstance, config.get, isinstance, f.strip, a.strip

### nlp-service.app.main.chat_start
> Rozpocznij nową konwersację. System rozpoznaje intencję i dopytuje o brakujące dane.

Obsługuje:
- Tekst: Form field "text"
- Audio: UploadFile (STT v
- **Calls**: app.post, Form, File, log.info, text.strip, HTTPException, nlp-service.app.orchestrator.start_conversation, nlp-service.app.audio_parser.is_stt_available

### nlp2dsl_sdk.client.NLP2DSLClient.from_env
> Build a client from environment variables used in this repo.
- **Calls**: os.getenv, os.getenv, os.getenv, float, cls, os.getenv, os.getenv, os.getenv

### nlp-service.app.settings.SettingsManager.update_section
> Update entire section from dict.
- **Calls**: getattr, data.items, ValueError, hasattr, None.isoformat, self._save, getattr, setattr

### worker.worker.execute_step
> Wykonuje pojedynczy krok workflow.
- **Calls**: app.post, step.get, step.get, step.get, ACTION_HANDLERS.get, log.info, HTTPException, handler

### backend.app.db.postgres.PostgresWorkflowRepo.save_run
- **Calls**: self._ensure_tables, WorkflowRunModel, session.add, log.debug, self._get_session_factory, session.commit, data.get, data.get

### nlp2dsl_sdk.client.ConversationFlow.run_interactive
- **Calls**: print, print, None.strip, text.lower, self.start, self.send_message, print, print

### nlp2dsl_sdk.__main__.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.parse_args, nlp2dsl_sdk.demos.list_available_demos, None.runner, print, parser.error

### backend.app.logging_setup.setup_logging
> Replace root logger handlers with a JSONFormatter handler.

Reads LOG_LEVEL from BackendSettings (default INFO). Call once at startup.
- **Calls**: level.upper, getattr, logging.StreamHandler, handler.setFormatter, logging.getLogger, root.handlers.clear, root.addHandler, root.setLevel

### nlp-service.app.logging_setup.setup_logging
> Replace root logger handlers with a JSONFormatter handler.

Reads LOG_LEVEL from NLPServiceSettings (default INFO). Call once at startup.
- **Calls**: level.upper, getattr, logging.StreamHandler, handler.setFormatter, logging.getLogger, root.handlers.clear, root.addHandler, root.setLevel

### nlp-service.app.system_executor._exec_registry_list
- **Calls**: config.get, ACTIONS_REGISTRY.items, meta.get, len, meta.get, list, None.keys, meta.get

### worker.logging_setup.setup_logging
> Replace root logger handlers with a JSONFormatter handler.

Reads LOG_LEVEL from WorkerSettings (default INFO). Call once at startup.
- **Calls**: level.upper, getattr, logging.StreamHandler, handler.setFormatter, logging.getLogger, root.handlers.clear, root.addHandler, root.setLevel

### worker.worker.handle_send_invoice
- **Calls**: worker.worker.action, log.info, log.info, config.get, config.get, asyncio.sleep, config.get, None.strftime

### worker.worker.handle_generate_report
- **Calls**: worker.worker.action, config.get, config.get, log.info, log.info, config.get, asyncio.sleep, None.strftime

### worker.worker.handle_send_email
- **Calls**: worker.worker.action, log.info, log.info, config.get, config.get, asyncio.sleep, config.get, config.get

### backend.app.db.postgres.PostgresWorkflowRepo.list_runs
- **Calls**: self._ensure_tables, None.all, self._get_session_factory, session.execute, text, result.mappings, None.isoformat

### backend.app.routers.chat.chat_get_state
> Pobierz stan konwersacji.
- **Calls**: router.get, resp.json, AsyncClient, HTTPException, client.get, float, backend.app.logging_setup.get_request_id

## Process Flows

Key execution flows identified:

### Flow 1: _handle_response
```
_handle_response [nlp2dsl_sdk.client.ConversationFlow]
```

### Flow 2: workflow_from_text
```
workflow_from_text [backend.app.routers.workflow]
```

### Flow 3: websocket_chat
```
websocket_chat [nlp-service.app.main]
  └─ →> is_stt_available
```

### Flow 4: run_action_catalog_demo
```
run_action_catalog_demo [nlp2dsl_sdk.demos]
  └─> _ensure_services
```

### Flow 5: _exec_file_read
```
_exec_file_read [nlp-service.app.system_executor]
  └─> _validate_file_path
```

### Flow 6: chat_message
```
chat_message [backend.app.routers.chat]
  └─> _proxy_chat_payload
```

### Flow 7: _exec_file_list
```
_exec_file_list [nlp-service.app.system_executor]
```

### Flow 8: handle_generate_code
```
handle_generate_code [worker.worker]
  └─> action
```

### Flow 9: _exec_registry_edit
```
_exec_registry_edit [nlp-service.app.system_executor]
```

### Flow 10: run_demo
```
run_demo [nlp2dsl_sdk.client.ConversationFlow]
```

## Key Classes

### nlp2dsl_sdk.client.NLP2DSLClient
> Small reusable SDK for the NLP2DSL services.
- **Methods**: 40
- **Key Methods**: nlp2dsl_sdk.client.NLP2DSLClient.__init__, nlp2dsl_sdk.client.NLP2DSLClient.from_env, nlp2dsl_sdk.client.NLP2DSLClient.close, nlp2dsl_sdk.client.NLP2DSLClient.__enter__, nlp2dsl_sdk.client.NLP2DSLClient.__exit__, nlp2dsl_sdk.client.NLP2DSLClient._request, nlp2dsl_sdk.client.NLP2DSLClient._backend, nlp2dsl_sdk.client.NLP2DSLClient._nlp_service, nlp2dsl_sdk.client.NLP2DSLClient._worker, nlp2dsl_sdk.client.NLP2DSLClient.backend_health

### nlp-service.app.settings.SettingsManager
> Runtime settings z persystencją do JSON.
- **Methods**: 11
- **Key Methods**: nlp-service.app.settings.SettingsManager.__new__, nlp-service.app.settings.SettingsManager.settings, nlp-service.app.settings.SettingsManager.get, nlp-service.app.settings.SettingsManager.get_section, nlp-service.app.settings.SettingsManager.get_all, nlp-service.app.settings.SettingsManager.set, nlp-service.app.settings.SettingsManager.update_section, nlp-service.app.settings.SettingsManager.reset, nlp-service.app.settings.SettingsManager._load, nlp-service.app.settings.SettingsManager._save

### backend.app.db.postgres.PostgresWorkflowRepo
- **Methods**: 10
- **Key Methods**: backend.app.db.postgres.PostgresWorkflowRepo.__init__, backend.app.db.postgres.PostgresWorkflowRepo._ensure_engine, backend.app.db.postgres.PostgresWorkflowRepo._get_session_factory, backend.app.db.postgres.PostgresWorkflowRepo._ensure_tables, backend.app.db.postgres.PostgresWorkflowRepo.save_run, backend.app.db.postgres.PostgresWorkflowRepo.update_run_status, backend.app.db.postgres.PostgresWorkflowRepo.get_run, backend.app.db.postgres.PostgresWorkflowRepo.list_runs, backend.app.db.postgres.PostgresWorkflowRepo.count_runs, backend.app.db.postgres.PostgresWorkflowRepo.close
- **Inherits**: WorkflowRepo

### nlp-service.app.code_generator.CodeGenerator
> Generates code in multiple programming languages using LLM.
- **Methods**: 8
- **Key Methods**: nlp-service.app.code_generator.CodeGenerator.__init__, nlp-service.app.code_generator.CodeGenerator._get_api_key, nlp-service.app.code_generator.CodeGenerator._build_prompt, nlp-service.app.code_generator.CodeGenerator.generate_code, nlp-service.app.code_generator.CodeGenerator._extract_class_name, nlp-service.app.code_generator.CodeGenerator._split_code_and_tests, nlp-service.app.code_generator.CodeGenerator.get_supported_languages, nlp-service.app.code_generator.CodeGenerator.get_language_info

### nlp-service.app.store.redis_store.RedisConversationStore
- **Methods**: 7
- **Key Methods**: nlp-service.app.store.redis_store.RedisConversationStore.__init__, nlp-service.app.store.redis_store.RedisConversationStore._key, nlp-service.app.store.redis_store.RedisConversationStore.get, nlp-service.app.store.redis_store.RedisConversationStore.save, nlp-service.app.store.redis_store.RedisConversationStore.delete, nlp-service.app.store.redis_store.RedisConversationStore.count, nlp-service.app.store.redis_store.RedisConversationStore.close
- **Inherits**: ConversationStore

### backend.app.db.memory.MemoryWorkflowRepo
- **Methods**: 6
- **Key Methods**: backend.app.db.memory.MemoryWorkflowRepo.__init__, backend.app.db.memory.MemoryWorkflowRepo.save_run, backend.app.db.memory.MemoryWorkflowRepo.update_run_status, backend.app.db.memory.MemoryWorkflowRepo.get_run, backend.app.db.memory.MemoryWorkflowRepo.list_runs, backend.app.db.memory.MemoryWorkflowRepo.count_runs
- **Inherits**: WorkflowRepo

### nlp2dsl_sdk.client.ConversationFlow
> Convenience helper for the conversational workflow example.
- **Methods**: 6
- **Key Methods**: nlp2dsl_sdk.client.ConversationFlow.__init__, nlp2dsl_sdk.client.ConversationFlow.start, nlp2dsl_sdk.client.ConversationFlow.send_message, nlp2dsl_sdk.client.ConversationFlow._handle_response, nlp2dsl_sdk.client.ConversationFlow.run_demo, nlp2dsl_sdk.client.ConversationFlow.run_interactive

### backend.app.db.WorkflowRepo
> Abstrakcja persystencji workflow.
- **Methods**: 5
- **Key Methods**: backend.app.db.WorkflowRepo.save_run, backend.app.db.WorkflowRepo.update_run_status, backend.app.db.WorkflowRepo.get_run, backend.app.db.WorkflowRepo.list_runs, backend.app.db.WorkflowRepo.count_runs
- **Inherits**: ABC

### nlp-service.app.audio_parser.StreamingSTT
> Real-time streaming STT via Deepgram WebSocket.
Placeholder - requires WebSocket implementation.
- **Methods**: 5
- **Key Methods**: nlp-service.app.audio_parser.StreamingSTT.__init__, nlp-service.app.audio_parser.StreamingSTT.start, nlp-service.app.audio_parser.StreamingSTT.send_audio, nlp-service.app.audio_parser.StreamingSTT.get_transcript, nlp-service.app.audio_parser.StreamingSTT.stop

### nlp-service.app.store.memory.MemoryConversationStore
- **Methods**: 5
- **Key Methods**: nlp-service.app.store.memory.MemoryConversationStore.__init__, nlp-service.app.store.memory.MemoryConversationStore.get, nlp-service.app.store.memory.MemoryConversationStore.save, nlp-service.app.store.memory.MemoryConversationStore.delete, nlp-service.app.store.memory.MemoryConversationStore.count
- **Inherits**: ConversationStore

### nlp-service.app.store.ConversationStore
> Abstrakcja persystencji stanu konwersacji.
- **Methods**: 4
- **Key Methods**: nlp-service.app.store.ConversationStore.get, nlp-service.app.store.ConversationStore.save, nlp-service.app.store.ConversationStore.delete, nlp-service.app.store.ConversationStore.count
- **Inherits**: ABC

### backend.app.logging_setup.JSONFormatter
> Emit log records as single-line JSON objects.
- **Methods**: 2
- **Key Methods**: backend.app.logging_setup.JSONFormatter.__init__, backend.app.logging_setup.JSONFormatter.format
- **Inherits**: logging.Formatter

### backend.app.logging_setup.RequestIDMiddleware
> Generate or forward X-Request-ID for every HTTP request.

- Reads X-Request-ID from incoming headers
- **Methods**: 2
- **Key Methods**: backend.app.logging_setup.RequestIDMiddleware.__init__, backend.app.logging_setup.RequestIDMiddleware.dispatch
- **Inherits**: BaseHTTPMiddleware

### nlp-service.app.logging_setup.JSONFormatter
> Emit log records as single-line JSON objects.
- **Methods**: 2
- **Key Methods**: nlp-service.app.logging_setup.JSONFormatter.__init__, nlp-service.app.logging_setup.JSONFormatter.format
- **Inherits**: logging.Formatter

### nlp-service.app.logging_setup.RequestIDMiddleware
> Generate or forward X-Request-ID for every HTTP request.

- Reads X-Request-ID from incoming headers
- **Methods**: 2
- **Key Methods**: nlp-service.app.logging_setup.RequestIDMiddleware.__init__, nlp-service.app.logging_setup.RequestIDMiddleware.dispatch
- **Inherits**: BaseHTTPMiddleware

### worker.logging_setup.JSONFormatter
> Emit log records as single-line JSON objects.
- **Methods**: 2
- **Key Methods**: worker.logging_setup.JSONFormatter.__init__, worker.logging_setup.JSONFormatter.format
- **Inherits**: logging.Formatter

### worker.logging_setup.RequestIDMiddleware
> Generate or forward X-Request-ID for every HTTP request.

- Reads X-Request-ID from incoming headers
- **Methods**: 2
- **Key Methods**: worker.logging_setup.RequestIDMiddleware.__init__, worker.logging_setup.RequestIDMiddleware.dispatch
- **Inherits**: BaseHTTPMiddleware

### backend.app.db.postgres.WorkflowRunModel
- **Methods**: 1
- **Key Methods**: backend.app.db.postgres.WorkflowRunModel.to_dict
- **Inherits**: Base

### backend.app.db.postgres.Base
- **Methods**: 0
- **Inherits**: DeclarativeBase

### nlp2dsl_sdk.demos.DemoSpec
> Metadata for a runnable demo exposed by the package CLI.
- **Methods**: 0

## Data Transformation Functions

Key functions that process and transform data:

### backend.app.logging_setup.JSONFormatter.format
- **Output to**: json.dumps, time.strftime, _request_id.get, record.getMessage, self.formatException

### nlp-service.app.parser_rules.parse_rules
> Parse text using rules — no LLM needed.
- **Output to**: text.lower, nlp-service.app.parser_rules._detect_actions, nlp-service.app.parser_rules._resolve_intent, nlp-service.app.parser_rules._extract_entities, nlp-service.app.registry.get_trigger

### nlp-service.app.logging_setup.JSONFormatter.format
- **Output to**: json.dumps, time.strftime, _request_id.get, record.getMessage, self.formatException

### nlp-service.app.orchestrator._process_message
> Core orchestration: parse → merge → validate → respond.
- **Output to**: nlp-service.app.parser_rules.parse_rules, log.info, nlp-service.app.orchestrator._merge_into_state, NLPResult, nlp-service.app.mapper.map_to_dsl

### nlp-service.app.orchestrator._format_system_result
> Format system action result as human-readable message.
- **Output to**: result.get, json.dumps, result.get, inner.get, inner.get

### nlp-service.app.system_executor._validate_file_path
> Validate and resolve file path against allowed paths.
- **Output to**: str, any, None.suffix.lower, None.resolve, PermissionError

### worker.logging_setup.JSONFormatter.format
- **Output to**: json.dumps, time.strftime, _request_id.get, record.getMessage, self.formatException

### nlp-service.app.main.parse_text
> Etap 1: tekst → intent + entities.
Nie generuje DSL — tylko rozumie język naturalny.
- **Output to**: app.post, nlp-service.app.main._run_parser

### nlp-service.app.main._run_parser
> Execute parser according to mode.
- **Output to**: nlp-service.app.parser_rules.parse_rules, nlp-service.app.parser_llm._detect_provider, nlp-service.app.parser_rules.parse_rules, nlp-service.app.parser_llm._detect_provider, log.info

### nlp-service.app.parser_llm.parse_llm
> Parse text using LLM via LiteLLM.
- **Output to**: nlp-service.app.parser_llm._detect_provider, log.info, log.debug, nlp-service.app.parser_llm._parse_json_response, NLPResult

### nlp-service.app.parser_llm._parse_json_response
> Extract JSON from LLM response (handles markdown fences).
- **Output to**: raw.strip, cleaned.startswith, cleaned.find, json.loads, cleaned.split

## Behavioral Patterns

### state_machine_NLP2DSLClient
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: nlp2dsl_sdk.client.NLP2DSLClient.__init__, nlp2dsl_sdk.client.NLP2DSLClient.from_env, nlp2dsl_sdk.client.NLP2DSLClient.close, nlp2dsl_sdk.client.NLP2DSLClient.__enter__, nlp2dsl_sdk.client.NLP2DSLClient.__exit__

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `nlp2dsl_sdk.demos.run_code_generation_demo` - 51 calls
- `backend.app.routers.workflow.workflow_from_text` - 26 calls
- `nlp-service.app.main.websocket_chat` - 23 calls
- `backend.app.engine.run_workflow` - 22 calls
- `nlp2dsl_sdk.demos.run_action_catalog_demo` - 19 calls
- `backend.app.routers.chat.chat_message` - 17 calls
- `nlp-service.app.mapper.map_to_dsl` - 17 calls
- `worker.worker.handle_generate_code` - 17 calls
- `nlp-service.app.parser_llm.parse_llm` - 16 calls
- `nlp2dsl_sdk.demos.run_invoice_demo` - 14 calls
- `nlp2dsl_sdk.demos.run_email_demo` - 14 calls
- `nlp2dsl_sdk.client.ConversationFlow.run_demo` - 14 calls
- `nlp-service.app.audio_parser.stt_audio` - 14 calls
- `nlp-service.app.code_generator.CodeGenerator.generate_code` - 13 calls
- `nlp-service.app.main.chat_message` - 13 calls
- `nlp-service.app.orchestrator.get_action_form` - 12 calls
- `nlp-service.app.main.chat_start` - 12 calls
- `nlp2dsl_sdk.demos.run_report_and_notify_demo` - 11 calls
- `nlp2dsl_sdk.client.NLP2DSLClient.from_env` - 11 calls
- `nlp-service.app.settings.SettingsManager.set` - 11 calls
- `tauri-wrapper.scripts.dev.main` - 10 calls
- `nlp2dsl_sdk.demos.run_scheduled_report_demo` - 10 calls
- `nlp-service.app.parser_rules.parse_rules` - 10 calls
- `nlp-service.app.settings.SettingsManager.update_section` - 10 calls
- `worker.worker.execute_step` - 10 calls
- `backend.app.db.postgres.PostgresWorkflowRepo.save_run` - 9 calls
- `nlp2dsl_sdk.client.ConversationFlow.run_interactive` - 9 calls
- `nlp2dsl_sdk.__main__.main` - 9 calls
- `backend.app.logging_setup.setup_logging` - 9 calls
- `nlp-service.app.logging_setup.setup_logging` - 9 calls
- `worker.logging_setup.setup_logging` - 9 calls
- `worker.worker.handle_send_invoice` - 9 calls
- `worker.worker.handle_generate_report` - 9 calls
- `nlp-service.app.orchestrator.continue_conversation` - 8 calls
- `worker.worker.handle_send_email` - 8 calls
- `backend.app.db.postgres.PostgresWorkflowRepo.list_runs` - 7 calls
- `backend.app.routers.chat.chat_get_state` - 7 calls
- `nlp2dsl_sdk.demos.run_crm_update_demo` - 7 calls
- `nlp-service.app.store.factory.get_conversation_store` - 7 calls
- `nlp-service.app.settings.SettingsManager.reset` - 7 calls

## System Interactions

How components interact:

```mermaid
graph TD
    _handle_response --> get
    _handle_response --> append
    _handle_response --> print
    workflow_from_text --> post
    workflow_from_text --> get
    workflow_from_text --> json
    websocket_chat --> websocket
    websocket_chat --> info
    websocket_chat --> accept
    websocket_chat --> is_stt_available
    websocket_chat --> StreamingSTT
    run_action_catalog_d --> print
    run_action_catalog_d --> workflow_actions
    run_action_catalog_d --> from_env
    run_action_catalog_d --> _ensure_services
    _exec_file_read --> get
    _exec_file_read --> _validate_file_path
    _exec_file_read --> read_text
    chat_message --> post
    chat_message --> json
    chat_message --> lower
    chat_message --> _proxy_chat_payload
    chat_message --> HTTPException
    _exec_file_list --> get
    _exec_file_list --> sorted
    _exec_file_list --> exists
    _exec_file_list --> Path
    handle_generate_code --> action
    handle_generate_code --> get
    _exec_registry_edit --> get
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.