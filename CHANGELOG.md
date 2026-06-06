# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.10] - 2026-06-05

### Fixed
- Fix unused-imports issues (ticket-59eadd57)

## [0.1.10] - 2026-06-05

### Fixed
- Fix unused-imports issues (ticket-808f0627)
- Fix unused-imports issues (ticket-ae593814)
- Fix unused-imports issues (ticket-f8a324eb)
- Fix string-concat issues (ticket-71a31124)
- Fix unused-imports issues (ticket-6eedcc0d)
- Fix unused-imports issues (ticket-c5647da9)
- Fix relative-imports issues (ticket-61a1ce8a)
- Fix unused-imports issues (ticket-99d85fdb)
- Fix ai-boilerplate issues (ticket-93020831)
- Fix relative-imports issues (ticket-16d87497)
- Fix unused-imports issues (ticket-35431ebc)
- Fix llm-hallucinations issues (ticket-04b8c97a)
- Fix magic-numbers issues (ticket-c914348e)
- Fix llm-generated-code issues (ticket-cc77397e)
- Fix smart-return-type issues (ticket-b7b9d421)
- Fix unused-imports issues (ticket-1f4e1aa2)
- Fix string-concat issues (ticket-9e34bb51)
- Fix llm-hallucinations issues (ticket-5e716bad)
- Fix relative-imports issues (ticket-9aeb0d35)
- Fix unused-imports issues (ticket-46df90a5)
- Fix relative-imports issues (ticket-e16eb7d9)
- Fix unused-imports issues (ticket-4952538e)
- Fix magic-numbers issues (ticket-04696266)
- Fix unused-imports issues (ticket-6dba0796)
- Fix unused-imports issues (ticket-018e66cc)
- Fix unused-imports issues (ticket-cf108012)
- Fix smart-return-type issues (ticket-f9fd0150)
- Fix unused-imports issues (ticket-1fb59192)
- Fix unused-imports issues (ticket-6b52261f)
- Fix unused-imports issues (ticket-9e1b41d4)
- Fix llm-generated-code issues (ticket-fec1d591)
- Fix unused-imports issues (ticket-90f4d3d2)
- Fix unused-imports issues (ticket-90757fae)
- Fix relative-imports issues (ticket-6ecbbbfd)
- Fix smart-return-type issues (ticket-7e98f326)
- Fix string-concat issues (ticket-6af3ff9e)
- Fix unused-imports issues (ticket-b4559ca8)
- Fix llm-generated-code issues (ticket-efd5460e)
- Fix unused-imports issues (ticket-59c32939)
- Fix unused-imports issues (ticket-8c51127d)
- Fix unused-imports issues (ticket-d73753dc)

## [Unreleased]

### Added
- Automatyczne kodowanie UTF-8 przy imporcie `nlp2dsl_sdk` i w CLI (`configure_utf8` bez ręcznego `export LANG`)
- Dokumentacja: [`docs/encoding.md`](docs/encoding.md)
- Artefakty przykładów `examples/*/.nlp2dsl/` — DOQL env, testql, pipeline JSON/YAML, process YAML (`nlp2dsl_sdk/artifacts.py`)
- `examples/bootstrap.py`, `scripts/aggregate-example-testql.py`, [`docs/artifacts.md`](docs/artifacts.md)

### Changed
- Audyt examples 01–12 + `demos.py`: wykonanie wyłącznie przez NLP (`workflow_from_text(execute=True)` / `ConversationFlow`); usunięto `ACTION_SAMPLE_RUNNERS` i gallery `runner` lambdas
- `execute_text_examples()` — batch execute z promptem przy `incomplete`
- Przykłady 01–04: wykonanie przez `workflow_from_text(execute=True)` zamiast hardkodu `send_email` / `create_scheduled_report`
- `examples/*/main.py`: ładowanie `scenario.py` przez `importlib` (naprawa kolizji `import scenario`)
- `execute_from_text()` w `nlp2dsl_sdk/preview.py`
- `configure_utf8` podnosi locale ASCII (`C`, `POSIX`) do `C.UTF-8`; rekonfiguruje też `stdin`
- Przykłady `examples/*/scenario.py` — usunięte ręczne wywołania `configure_utf8(force=True)`
- `nlp2dsl-show` deleguje encoding do SDK gdy dostępny

### Fixed
- `nlp2cmd-intent`: normalizer zwracający `str` zamiast obiektu z `.text` w `KeywordIntentDetector`

## [0.0.29] - 2026-06-06

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/REFACTOR-PLAN.md
- Update docs/ROADMAP-30-60-90.md
- Update docs/process-agent.md
- Update docs/validation.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/test_doql_context.py
- Update tests/test_validation.py

### Other
- Update app.doql.less
- Update backend/app/action_catalog.py
- Update backend/app/attachment_validation.py
- Update backend/app/routers/chat.py
- Update backend/app/routers/workflow.py
- Update backend/app/step_validator.py
- Update backend/tests/test_action_catalog.py
- Update backend/tests/test_chat_execute_keywords.py
- Update backend/tests/test_workflow_api.py
- Update examples/07-email-conversation/scenario.py
- ... and 64 more files

## [0.0.28] - 2026-06-06

### Docs
- Update README.md

### Other
- Update examples/08-multi-object-benchmark/results/benchmark_1780738565.json
- Update examples/testql-results.json
- Update nlp-service/app/conversation/merge.py
- Update nlp-service/app/conversation/system_map.py
- Update nlp-service/app/execution/system.py
- Update nlp-service/app/main.py
- Update nlp-service/app/registry.py
- Update nlp-service/app/routing/native.py
- Update nlp-service/app/routing/parser/intent_normalize.py
- Update nlp-service/app/routing/parser/prompt_catalog.py
- ... and 5 more files

## [0.0.27] - 2026-06-06

### Docs
- Update README.md

### Other
- Update examples/08-multi-object-benchmark/results/benchmark_1780738187.json
- Update nlp-service/app/conversation/system_map.py
- Update nlp-service/app/dsl/forms.py
- Update nlp-service/app/dsl/mapper.py
- Update nlp-service/app/registry.py
- Update nlp-service/app/routing/parser/rules.py
- Update nlp2dsl_sdk/doql/context_blocks.py
- Update nlp2dsl_sdk/doql/render.py
- Update nlp2dsl_sdk/encoding.py

## [0.0.26] - 2026-06-06

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/README.md
- Update docs/REFACTOR-PLAN.md
- Update docs/artifacts.md
- Update docs/autonomous-stack.md
- Update docs/doql-system-map.md
- ... and 6 more files

### Test
- Update testql-scenarios/generated-examples.testql.toon.yaml
- Update tests/test_attachment_validation.py
- Update tests/test_doql_context.py
- Update tests/test_doql_registry.py
- Update tests/test_invoice_pdf.py
- Update tests/test_invoice_policy.py
- Update tests/test_nlp2dsl_sdk.py
- Update tests/test_path_resolve.py
- Update tests/test_process_policy.py
- Update tests/test_profile_validations.py
- ... and 2 more files

### Other
- Update app.doql.less
- Update backend/Dockerfile
- Update backend/app/attachment_validation.py
- Update backend/app/dsl_validation.py
- Update backend/app/path_resolve.py
- Update backend/app/routers/chat.py
- Update backend/app/routers/workflow.py
- Update backend/app/step_validator.py
- Update backend/tests/conftest.py
- Update backend/tests/test_attachment_validation.py
- ... and 114 more files

## [0.0.25] - 2026-06-05

### Docs
- Update README.md

### Other
- Update nlp-service/tests/test_routing_resolve.py

## [0.0.24] - 2026-06-05

### Docs
- Update README.md

## [0.0.23] - 2026-06-05

### Docs
- Update README.md

### Test
- Update tests/test_conversation_testql.py

### Other
- Update .gitattributes
- Update nlp2dsl_sdk/conversation_testql.py
- Update run-all-tests.sh
- Update scripts/bootstrap-venv.sh
- Update uv.lock

## [0.0.22] - 2026-06-05

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/artifacts.md
- Update docs/autonomous-stack.md
- Update docs/doql-dynamic-generation.md
- Update docs/doql-runtimes.md
- Update docs/doql-system-map.md
- Update docs/process-agent.md
- ... and 4 more files

### Test
- Update testql-scenarios/generated-examples.testql.toon.yaml
- Update tests/test_artifact_layout.py
- Update tests/test_compose_generator.py
- Update tests/test_conversation_testql.py
- Update tests/test_doql_registry.py
- Update tests/test_path_resolve.py
- Update tests/test_reflection.py
- Update tests/test_system_map_ir.py

### Other
- Update .gitignore
- Update VERSION
- Update app.doql.less
- Update backend/app/engine.py
- Update backend/app/main.py
- Update backend/app/path_resolve.py
- Update backend/app/routers/chat.py
- Update backend/app/routers/testql_compat.py
- Update backend/app/step_validator.py
- Update backend/tests/test_step_validator.py
- ... and 87 more files

## [0.0.19] - 2026-06-05

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update examples/README.md
- Update project/README.md
- Update project/context.md

### Test
- Update testql-scenarios/generated-examples.testql.toon.yaml

### Other
- Update .gitignore
- Update app.doql.less
- Update examples/08-multi-object-benchmark/results/benchmark_1780673613.json
- Update examples/11-notify-quality/scenario.py
- Update examples/12-ir-show/scenario.py
- Update examples/run-all.sh
- Update examples/testql-results.json
- Update nlp2dsl_sdk/demos.py
- Update nlp2dsl_sdk/preview.py
- Update planfile.yaml
- ... and 19 more files

## [0.0.18] - 2026-06-05

### Docs
- Update CHANGELOG.md
- Update README.md
- Update examples/README.md

### Test
- Update testql-scenarios/generated-examples.testql.toon.yaml

### Other
- Update examples/01-invoice/main.py
- Update examples/01-invoice/scenario.py
- Update examples/02-email/main.py
- Update examples/02-email/scenario.py
- Update examples/03-report-and-notify/main.py
- Update examples/03-report-and-notify/scenario.py
- Update examples/04-scheduled-report/main.py
- Update examples/04-scheduled-report/scenario.py
- Update examples/05-conversation-flow/main.py
- Update examples/06-interactive-chat/main.py
- ... and 8 more files

## [0.1.10] - 2026-06-05

### Fixed
- Fix unused-imports issues (ticket-4db4052e)
- Fix string-concat issues (ticket-58f905e2)

## [0.1.10] - 2026-06-04

### Fixed
- Fix unused-imports issues (ticket-a26d26be)
- Fix unused-imports issues (ticket-c5c0bd6b)

## [0.1.10] - 2026-06-04

### Fixed
- Fix wildcard-imports issues (ticket-caf9a1b0)
- Fix wildcard-imports issues (ticket-4e2b622d)
- Fix wildcard-imports issues (ticket-63459fc2)
- Fix wildcard-imports issues (ticket-c5eb32c9)
- Fix wildcard-imports issues (ticket-ac0a3b35)
- Fix unused-imports issues (ticket-b5420121)
- Fix string-concat issues (ticket-eb8d37d9)
- Fix unused-imports issues (ticket-4412b3a3)
- Fix string-concat issues (ticket-806ddaa3)
- Fix unused-imports issues (ticket-2788505d)
- Fix string-concat issues (ticket-c7829562)
- Fix unused-imports issues (ticket-b70fd2b3)
- Fix unused-imports issues (ticket-5d778247)
- Fix unused-imports issues (ticket-5df050fb)
- Fix unused-imports issues (ticket-23772558)
- Fix unused-imports issues (ticket-ed906b0a)
- Fix string-concat issues (ticket-52633c6e)
- Fix string-concat issues (ticket-cdff8572)

## [0.1.10] - 2026-06-04

### Fixed
- Fix unused-imports issues (ticket-4548f541)
- Fix unused-imports issues (ticket-1f25c667)

## [0.1.10] - 2026-06-04

### Fixed
- Fix unused-imports issues (ticket-570b8c9f)
- Fix string-concat issues (ticket-29c93a43)
- Fix unused-imports issues (ticket-6e22a6eb)
- Fix unused-imports issues (ticket-9aae9951)
- Fix unused-imports issues (ticket-9b8ea132)
- Fix unused-imports issues (ticket-dbf1ee9e)
- Fix unused-imports issues (ticket-9f0f5f67)

## [0.1.10] - 2026-06-04

### Fixed
- Fix string-concat issues (ticket-be57afc5)
- Fix unused-imports issues (ticket-167e0f6b)
- Fix unused-imports issues (ticket-f2668f83)
- Fix smart-return-type issues (ticket-70ded9e5)

## [0.1.10] - 2026-06-03

### Fixed
- Fix string-concat issues (ticket-616e3a85)
- Fix string-concat issues (ticket-c3e00438)
- Fix magic-numbers issues (ticket-0c14fdca)
- Fix string-concat issues (ticket-891a6624)
- Fix unused-imports issues (ticket-fee55e46)
- Fix wildcard-imports issues (ticket-8d40f43b)
- Fix ai-boilerplate issues (ticket-08ceb54b)
- Fix string-concat issues (ticket-619416fc)
- Fix relative-imports issues (ticket-e831df43)
- Fix relative-imports issues (ticket-611cce1f)
- Fix unused-imports issues (ticket-b262a15d)
- Fix ai-boilerplate issues (ticket-1ca41d5c)
- Fix string-concat issues (ticket-3c002d51)
- Fix unused-imports issues (ticket-a21e2790)
- Fix magic-numbers issues (ticket-8347ee63)
- Fix relative-imports issues (ticket-c817bf01)
- Fix unused-imports issues (ticket-8b296193)
- Fix magic-numbers issues (ticket-6e5993f0)
- Fix llm-generated-code issues (ticket-d5835930)
- Fix unused-imports issues (ticket-56520637)
- Fix unused-imports issues (ticket-2b6c5439)
- Fix string-concat issues (ticket-1524c8eb)
- Fix unused-imports issues (ticket-75152068)
- Fix string-concat issues (ticket-18143572)
- Fix unused-imports issues (ticket-b115c49b)
- Fix unused-imports issues (ticket-e018aebb)
- Fix magic-numbers issues (ticket-09a381ab)
- Fix unused-imports issues (ticket-e1c59dbb)
- Fix unused-imports issues (ticket-e274cbe7)
- Fix smart-return-type issues (ticket-cf621da7)
- Fix relative-imports issues (ticket-f0bb0d83)
- Fix relative-imports issues (ticket-1d8f8c0a)
- Fix string-concat issues (ticket-2a0f4b01)

## [Unreleased]

## [0.0.17] - 2026-06-05

### Docs
- Update README.md

### Other
- Update .env.example
- Update examples/08-multi-object-benchmark/results/benchmark_1780672441.json
- Update nlp-service/app/conversation/merge.py
- Update nlp-service/app/conversation/responses.py
- Update nlp-service/app/routing/parser/rules.py
- Update nlp-service/tests/test_orchestrator.py
- Update nlp-service/tests/test_parser_rules.py

## [0.0.16] - 2026-06-05

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/intract-integration.md
- Update examples/README.md
- Update packages/README.md
- Update packages/nlp2cmd-intent/README.md
- Update packages/nlp2cmd-planner/README.md
- ... and 5 more files

### Test
- Update tests/test_encoding.py
- Update tests/test_nlp2dsl_sdk.py

### Other
- Update .env.example
- Update Makefile
- Update app.doql.less
- Update backend/app/db/postgres.py
- Update backend/app/routers/workflow.py
- Update examples/01-invoice/main.py
- Update examples/01-invoice/scenario.py
- Update examples/02-email/main.py
- Update examples/02-email/scenario.py
- Update examples/03-report-and-notify/main.py
- ... and 133 more files

## [0.0.15] - 2026-06-04

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Other
- Update .env.example
- Update app.doql.less
- Update planfile.yaml
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- ... and 11 more files

## [0.0.14] - 2026-06-04

### Docs
- Update README.md

### Other
- Update .env.example
- Update nlp-service/app/conversation/responses.py

## [0.0.13] - 2026-06-04

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update docs/REFACTOR-PLAN.md
- Update docs/access-control.md
- Update project/README.md
- Update project/context.md

### Other
- Update .env.example
- Update app.doql.less
- Update backend/requirements.txt
- Update nlp-service/app/access/__init__.py
- Update nlp-service/app/access/bootstrap.py
- Update nlp-service/app/access/config.py
- Update nlp-service/app/access/native.py
- Update nlp-service/app/access/policy.py
- Update nlp-service/app/access/uri_match.py
- Update nlp-service/app/main.py
- ... and 28 more files

## [0.0.12] - 2026-06-04

### Docs
- Update README.md
- Update docs/REFACTOR-PLAN.md
- Update project/README.md
- Update project/context.md

### Other
- Update .env.example
- Update backend/app/routers/chat.py
- Update nlp-service/Dockerfile
- Update nlp-service/app/orchestrator.py
- Update nlp-service/app/parser_rules.py
- Update nlp-service/app/parsing/__init__.py
- Update nlp-service/app/parsing/facade.py
- Update nlp-service/app/registry.py
- Update nlp-service/app/schemas.py
- Update nlp-service/integrations/__init__.py
- ... and 23 more files

## [0.0.11] - 2026-06-03

### Docs
- Update README.md

## [0.0.10] - 2026-06-03

### Docs
- Update README.md

### Test
- Update tests/test_tests.py

## [0.0.9] - 2026-06-03

### Docs
- Update README.md

## [0.0.8] - 2026-06-03

### Docs
- Update CHANGELOG.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update TODO.md
- Update project/README.md
- Update project/context.md

### Test
- Update testql-scenarios/generated-api-smoke.testql.toon.yaml
- Update testql-scenarios/generated-cli-tests.testql.toon.yaml
- Update testql-scenarios/generated-from-pytests.testql.toon.yaml
- Update tests/tests/test_nlp2dsl_tests.py

### Other
- Update app.doql.less
- Update nlp-service/app/main.py
- Update nlp-service/app/orchestrator.py
- Update nlp-service/app/parser_rules.py
- Update nlp-service/app/system_executor.py
- Update nlp2dsl_sdk/client.py
- Update nlp2dsl_sdk/demos.py
- Update planfile.yaml
- Update project.sh
- Update project/analysis.toon.yaml
- ... and 19 more files

## [0.0.7] - 2026-04-07

### Docs
- Update README.md
- Update docs/README.md
- Update examples/01-invoice/README.md
- Update examples/02-email/README.md
- Update examples/03-report-and-notify/README.md
- Update examples/04-scheduled-report/README.md
- Update examples/05-conversation-flow/README.md
- Update examples/README.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/.gitignore
- Update tests/e2e/conftest.py
- Update tests/pytest.ini
- Update tests/test_nlp2dsl_sdk.py
- Update tests/tests/test_tests.py

### Other
- Update .gitignore
- Update backend/.gitignore
- Update backend/app/db/__init__.py
- Update backend/app/db/postgres.py
- Update backend/tests/conftest.py
- Update examples/01-invoice/Dockerfile
- Update examples/01-invoice/main.py
- Update examples/01-invoice/requirements.txt
- Update examples/01-invoice/run.sh
- Update examples/02-email/Dockerfile
- ... and 43 more files

## [0.0.6] - 2026-04-07

### Test
- Update test_code_generation.py

### Other
- Update backend/app/logging_setup.py
- Update examples/01-invoice/main.py
- Update examples/02-email/main.py
- Update examples/03-report-and-notify/main.py
- Update examples/04-scheduled-report/main.py
- Update examples/05-conversation-flow/main.py
- Update examples/code_generation_examples.py
- Update nlp-service/app/code_generator.py
- Update worker/worker.py

## [0.0.5] - 2026-04-07

### Docs
- Update docs/README.md
- Update project/README.md
- Update project/context.md

### Other
- Update backend/app/config.py
- Update backend/app/db/__init__.py
- Update backend/app/db/memory.py
- Update backend/app/db/postgres.py
- Update backend/app/engine.py
- Update backend/app/logging_setup.py
- Update backend/app/main.py
- Update backend/app/routers/chat.py
- Update backend/app/routers/settings.py
- Update backend/app/routers/system.py
- ... and 55 more files

## [0.0.4] - 2026-04-06

### Docs
- Update README.md
- Update docs/README.md
- Update docs/migration-persistence.md
- Update examples/MISSING_CONFIGURATION.md
- Update project/README.md
- Update project/context.md
- Update tauri-wrapper/README.md

### Other
- Update .env.example
- Update backend/app/db/__init__.py
- Update backend/app/db/memory.py
- Update backend/app/db/postgres.py
- Update backend/app/workflow.py
- Update backend/requirements.txt
- Update nlp-service/app/audio_parser.py
- Update nlp-service/app/main.py
- Update nlp-service/app/orchestrator.py
- Update nlp-service/app/store/__init__.py
- ... and 29 more files

## [0.0.3] - 2026-04-06

### Docs
- Update README.md
- Update docs/README.md
- Update examples/01-invoice/README.md
- Update examples/02-email/README.md
- Update examples/03-report-and-notify/README.md
- Update examples/04-scheduled-report/README.md
- Update examples/05-conversation-flow/README.md
- Update examples/README.md
- Update project/README.md
- Update project/context.md

### Other
- Update .env.example
- Update examples/01-invoice/.env.example
- Update examples/01-invoice/Dockerfile
- Update examples/01-invoice/main.py
- Update examples/01-invoice/requirements.txt
- Update examples/01-invoice/run.sh
- Update examples/02-email/.env.example
- Update examples/02-email/Dockerfile
- Update examples/02-email/main.py
- Update examples/02-email/requirements.txt
- ... and 36 more files

## [0.0.2] - 2026-04-06

### Docs
- Update README.md
- Update articles/adaptive-hypernet.md
- Update articles/conceptual-hcm.md
- Update articles/cure-core-hox-v2.md
- Update articles/drm-module-advanced.md
- Update articles/flow-network.md
- Update articles/hilbert-net.md
- Update articles/mvp-automation-platform.md
- Update articles/universal-binary-tensor.md

### Other
- Update .gitignore

## [0.0.1] - 2026-04-06

### Docs
- Update README.md

### Other
- Update .gitignore
- Update backend/Dockerfile
- Update backend/app/__init__.py
- Update backend/app/main.py
- Update backend/app/schemas.py
- Update backend/app/workflow.py
- Update backend/requirements.txt
- Update nlp-service/Dockerfile
- Update nlp-service/app/__init__.py
- Update nlp-service/app/main.py
- ... and 11 more files

