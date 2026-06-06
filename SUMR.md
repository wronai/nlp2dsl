# MVP Automation Platform

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `nlp2dsl`
- **version**: `0.0.25`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, testql(4), app.doql.less, pyqual.yaml, goal.yaml, .env.example, docker-compose.yml, project/(6 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: nlp2dsl;
  version: 0.0.25;
}

dependencies {
  runtime: "requests>=2.31.0, pyyaml>=6.0, pydantic>=2.0";
  dev: "pytest>=8.0, pytest-asyncio>=0.24";
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
  attachment_path: str | None;
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
  doql_context_path: str | None;
  doql_inline: json!;
  autofill_applied: list[str]!;
  attachment_required: bool!;
  autonomous_steps: list[str]!;
  execution: dict | None;
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

## Dependencies

### Runtime

```text markpact:deps python
requests>=2.31.0
pyyaml>=6.0
pydantic>=2.0
```

### Development

```text markpact:deps python scope=dev
pytest>=8.0
pytest-asyncio>=0.24
```

## Call Graph

*451 nodes · 500 edges · 107 modules · CC̄=4.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `render_system_map_doql` *(in nlp2dsl_sdk.system_map_render)* | 70 ⚠ | 5 | 164 | **169** |
| `render_doql_context` *(in nlp2dsl_sdk.doql.render)* | 62 ⚠ | 2 | 129 | **131** |
| `generate_stack_compose` *(in nlp2dsl_sdk.compose_generator)* | 13 ⚠ | 1 | 79 | **80** |
| `format_transcript` *(in nlp2dsl_sdk.conversation_artifacts)* | 25 ⚠ | 1 | 57 | **58** |
| `_execute_workflow` *(in backend.app.engine)* | 13 ⚠ | 2 | 50 | **52** |
| `_load_detector_config_from_json` *(in packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns)* | 33 ⚠ | 0 | 48 | **48** |
| `print_workflow_preview` *(in nlp2dsl_sdk.preview)* | 18 ⚠ | 8 | 38 | **46** |
| `process_policy_from_profile_block` *(in nlp2dsl_sdk.process_policy)* | 23 ⚠ | 1 | 45 | **46** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/wronai/nlp2dsl
# generated in 0.22s
# nodes: 451 | edges: 500 | modules: 107
# CC̄=4.7

HUBS[20]:
  nlp2dsl_sdk.system_map_render.render_system_map_doql
    CC=70  in:5  out:164  total:169
  nlp2dsl_sdk.doql.render.render_doql_context
    CC=62  in:2  out:129  total:131
  nlp2dsl_sdk.compose_generator.generate_stack_compose
    CC=13  in:1  out:79  total:80
  nlp2dsl_sdk.conversation_artifacts.format_transcript
    CC=25  in:1  out:57  total:58
  backend.app.engine._execute_workflow
    CC=13  in:2  out:50  total:52
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_detector_config_from_json
    CC=33  in:0  out:48  total:48
  nlp2dsl_sdk.preview.print_workflow_preview
    CC=18  in:8  out:38  total:46
  nlp2dsl_sdk.process_policy.process_policy_from_profile_block
    CC=23  in:1  out:45  total:46
  nlp2dsl_sdk.preview.print_run_outcome
    CC=21  in:1  out:40  total:41
  nlp-service.app.settings.SettingsManager.set
    CC=4  in:27  out:11  total:38
  nlp2dsl_sdk.system_map_runtimes.build_runtimes_for_example
    CC=18  in:1  out:35  total:36
  nlp2dsl_sdk.conversation_testql.validate_conversation_scenario
    CC=21  in:1  out:34  total:35
  nlp2dsl_sdk.doql.parse.collect_task_context
    CC=19  in:3  out:32  total:35
  backend.app.path_resolve.resolve_attachment_path
    CC=13  in:9  out:26  total:35
  examples.01-invoice.scenario.run
    CC=20  in:0  out:34  total:34
  nlp2dsl_sdk.doql.parse.load_platform_map
    CC=18  in:1  out:32  total:33
  nlp2dsl_sdk.system_map_bridge.task_context_to_system_map
    CC=24  in:3  out:29  total:32
  nlp2dsl_sdk.doql.parse.enrich_task_context_from_client
    CC=19  in:1  out:29  total:30
  nlp2dsl_sdk.artifacts.build_process_trace
    CC=17  in:1  out:29  total:30
  backend.app.routers.workflow.workflow_from_text
    CC=9  in:1  out:29  total:30

MODULES:
  backend.app.attachment_validation  [1 funcs]
    ensure_attachment_validation  CC=10  out:10
  backend.app.dsl_validation  [5 funcs]
    dsl_validation_response  CC=1  out:3
    format_dsl_validation_message  CC=2  out:4
    missing_fields_from_issues  CC=5  out:3
    validate_dsl_for_execution  CC=1  out:1
    validation_issue_payloads  CC=2  out:1
  backend.app.engine  [7 funcs]
    _execute_workflow  CC=13  out:50
    _persist_workflow_snapshot  CC=2  out:2
    _publish_workflow_event  CC=2  out:2
    _track_background_task  CC=1  out:5
    _workflow_steps_payload  CC=2  out:1
    run_workflow  CC=1  out:2
    start_workflow  CC=1  out:7
  backend.app.logging_setup  [1 funcs]
    get_request_id  CC=1  out:1
  backend.app.path_resolve  [2 funcs]
    _examples_portable_candidates  CC=8  out:16
    resolve_attachment_path  CC=13  out:26
  backend.app.routers.chat  [19 funcs]
    _doql_context_path  CC=2  out:2
    _dsl_steps  CC=4  out:2
    _execute_ready_dsl  CC=5  out:16
    _execution_observation_from_dsl  CC=4  out:4
    _execution_requested  CC=2  out:2
    _is_auto_execute_requested  CC=3  out:4
    _is_explicit_execute_request  CC=2  out:4
    _mark_auto_execute_message  CC=6  out:9
    _maybe_auto_execute  CC=3  out:3
    _merge_attachment_validation  CC=9  out:7
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
  backend.app.routers.testql_compat  [8 funcs]
    _alias_response  CC=3  out:1
    _maybe_execute_on_message  CC=6  out:13
    _resolve_conv_id  CC=3  out:2
    _resolve_text  CC=8  out:8
    testql_chatmessage  CC=4  out:10
    testql_chatstart  CC=5  out:9
    testql_runworkflow  CC=4  out:17
    testql_workflow_from_text  CC=1  out:2
  backend.app.routers.workflow  [6 funcs]
    _format_sse  CC=5  out:6
    _workflow_snapshot  CC=1  out:7
    run_workflow_endpoint  CC=1  out:2
    start_workflow_endpoint  CC=1  out:2
    stream_workflow  CC=2  out:22
    workflow_from_text  CC=9  out:29
  backend.app.step_validator  [3 funcs]
    _validation_context  CC=1  out:5
    validate_step_config  CC=1  out:2
    validate_step_config_issues  CC=2  out:3
  backend.app.workflow_events  [2 funcs]
    publish  CC=2  out:4
    subscriber_count  CC=1  out:3
  examples.01-invoice.scenario  [4 funcs]
    _attachment_validation  CC=9  out:9
    _example_dir  CC=1  out:2
    _run_autonomous  CC=1  out:9
    run  CC=20  out:34
  examples.02-email.scenario  [1 funcs]
    run  CC=7  out:19
  examples.03-report-and-notify.scenario  [1 funcs]
    run  CC=6  out:17
  examples.04-scheduled-report.scenario  [1 funcs]
    run  CC=11  out:21
  examples.05-conversation-flow.scenario  [4 funcs]
    _save_conversation_artifacts  CC=1  out:2
    run  CC=2  out:2
    run_demo  CC=2  out:18
    run_interactive  CC=1  out:2
  examples.06-interactive-chat.scenario  [3 funcs]
    run  CC=2  out:2
    run_demo  CC=4  out:15
    run_interactive  CC=1  out:4
  examples.07-email-conversation.scenario  [1 funcs]
    run  CC=3  out:15
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
  examples.13-autonomous-invoice-stack.scenario  [1 funcs]
    run  CC=20  out:24
  examples.bootstrap  [1 funcs]
    bootstrap  CC=11  out:16
  examples.code_generation_examples  [1 funcs]
    main  CC=1  out:1
  nlp-service.app.audio_parser  [4 funcs]
    send_audio  CC=2  out:2
    is_stt_available  CC=2  out:0
    stt_audio  CC=9  out:14
    stt_file  CC=2  out:4
  nlp-service.app.conversation.attachment_gate  [1 funcs]
    workflow_needs_attachment  CC=8  out:4
  nlp-service.app.conversation.autonomous_loop  [6 funcs]
    _attachment_valid_ok  CC=7  out:7
    _example_dir  CC=3  out:5
    _maybe_delete_generated_attachment  CC=5  out:5
    _resolve_artifact_file  CC=7  out:13
    _step_config_for_validation  CC=4  out:2
    _try_fixture_attachment  CC=16  out:20
  nlp-service.app.conversation.doql_autofill  [2 funcs]
    _resolve_attachment_path  CC=1  out:2
    load_context_for_state  CC=8  out:5
  nlp-service.app.conversation.doql_registry  [7 funcs]
    _entities_to_data  CC=5  out:4
    _format_value  CC=4  out:5
    _patch_doql_file  CC=5  out:16
    _render_block  CC=2  out:5
    _try_sdk_refresh  CC=4  out:7
    refresh_registry_for_state  CC=16  out:21
    reload_context_after_refresh  CC=1  out:2
  nlp-service.app.conversation.invoice_policy  [2 funcs]
    invoice_attachment_policy_active  CC=9  out:2
    is_invoice_example  CC=2  out:1
  nlp-service.app.conversation.merge  [1 funcs]
    merge_into_state  CC=13  out:4
  nlp-service.app.conversation.orchestrator  [3 funcs]
    continue_conversation  CC=4  out:13
    get_conversation  CC=2  out:3
    start_conversation  CC=4  out:12
  nlp-service.app.conversation.runtime_gate  [2 funcs]
    process_scope_blocked  CC=12  out:7
    runtime_unavailable_message  CC=7  out:2
  nlp-service.app.conversation.system_map  [3 funcs]
    get_doql_context  CC=1  out:1
    runtime_id_for_action  CC=2  out:2
    set_doql_context  CC=1  out:1
  nlp-service.app.dsl.forms  [1 funcs]
    get_action_form  CC=5  out:12
  nlp-service.app.dsl.pipeline  [1 funcs]
    map_to_dsl_with_enrichment  CC=6  out:4
  nlp-service.app.execution.delegate  [3 funcs]
    execution_backend_for_intent  CC=5  out:4
    execution_backend_for_runtime  CC=4  out:0
    is_delegated_to_mullm  CC=2  out:1
  nlp-service.app.governance.config  [2 funcs]
    get_access_config  CC=1  out:1
    reload_access_config  CC=1  out:1
  nlp-service.app.governance.policy  [1 funcs]
    authorize_action  CC=5  out:8
  nlp-service.app.main  [16 funcs]
    _parse_context_json  CC=5  out:3
    _run_parser  CC=3  out:3
    access_check  CC=3  out:6
    access_config  CC=3  out:12
    access_reload  CC=2  out:2
    action_schema  CC=2  out:3
    actions_schema  CC=3  out:3
    chat_message  CC=6  out:15
    chat_start  CC=7  out:15
    chat_state  CC=2  out:4
  nlp-service.app.registry  [1 funcs]
    get_trigger  CC=3  out:2
  nlp-service.app.request_context  [1 funcs]
    get_example_dir  CC=2  out:3
  nlp-service.app.routing.observability  [1 funcs]
    routing_metrics_snapshot  CC=1  out:1
  nlp-service.app.routing.orientation  [1 funcs]
    orient_query  CC=16  out:27
  nlp-service.app.routing.parser.llm  [1 funcs]
    _detect_provider  CC=10  out:8
  nlp-service.app.routing.parser.resolve_mode  [1 funcs]
    parse_with_mode  CC=11  out:12
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
  nlp2dsl_sdk.__main__  [1 funcs]
    main  CC=5  out:10
  nlp2dsl_sdk.artifact_layout  [9 funcs]
    artifact_root  CC=1  out:2
    current_run_id  CC=2  out:4
    ensure_layout  CC=1  out:6
    resolve_registry_path  CC=9  out:11
    run_dir  CC=2  out:4
    write_last_run_report  CC=1  out:6
    write_reflection_snapshot  CC=1  out:8
    write_registry  CC=2  out:5
    write_turn_snapshot  CC=4  out:21
  nlp2dsl_sdk.artifacts  [14 funcs]
    __init__  CC=5  out:6
    finalize  CC=5  out:13
    record  CC=1  out:6
    _extract_actions  CC=4  out:5
    _mask_secret  CC=3  out:1
    _slugify  CC=2  out:5
    build_process_trace  CC=17  out:29
    collect_environment  CC=6  out:4
    example_artifact_root  CC=1  out:2
    get_example_writer  CC=2  out:4
  nlp2dsl_sdk.attachment_validation  [6 funcs]
    _apply_attachment_to_execution  CC=7  out:6
    _attachment_from_dsl  CC=8  out:10
    _prefer_local_validation  CC=4  out:2
    build_attachment_validation  CC=8  out:15
    enrich_chat_response  CC=11  out:12
    format_attachment_validation  CC=10  out:8
  nlp2dsl_sdk.autonomous_flow  [1 funcs]
    _start_with_extra  CC=6  out:22
  nlp2dsl_sdk.cli  [12 funcs]
    _actions  CC=3  out:8
    _analyze  CC=2  out:1
    _chat_start  CC=2  out:10
    _client  CC=1  out:1
    _demo  CC=6  out:5
    _detect_example_dir  CC=4  out:4
    _display  CC=13  out:27
    _health  CC=2  out:6
    _run  CC=5  out:9
    _run_with_doql  CC=6  out:12
  nlp2dsl_sdk.client  [18 funcs]
    _handle_completed_response  CC=14  out:22
    _persist_reflection  CC=11  out:18
    _print_attachment_validation  CC=3  out:3
    _record_turn  CC=1  out:2
    _reflect_executed_turn  CC=5  out:10
    _refresh_doql_registry  CC=13  out:15
    save_artifacts  CC=2  out:4
    start  CC=2  out:12
    chat_message  CC=6  out:11
    chat_start  CC=4  out:10
  nlp2dsl_sdk.compose_generator  [10 funcs]
    _default_deploy  CC=1  out:2
    _default_generated_services  CC=2  out:2
    _default_schedules  CC=1  out:1
    _run_process_docker_script  CC=1  out:1
    _run_process_host_script  CC=1  out:1
    _run_script_content  CC=2  out:3
    _stack_compose_dict  CC=8  out:10
    _wait_for_backend_shell  CC=1  out:1
    enrich_ir_for_stack  CC=5  out:5
    generate_stack_compose  CC=13  out:79
  nlp2dsl_sdk.conversation_artifacts  [3 funcs]
    _routing_summary  CC=6  out:4
    format_transcript  CC=25  out:57
    write_conversation_artifacts  CC=1  out:13
  nlp2dsl_sdk.conversation_testql  [3 funcs]
    _is_nlp_kind  CC=1  out:2
    dry_run_conversation_scenario  CC=1  out:1
    validate_conversation_scenario  CC=21  out:34
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
  nlp2dsl_sdk.doql.parse  [23 funcs]
    _append_collection_blocks  CC=10  out:15
    _apply_capabilities_block  CC=5  out:7
    _apply_context_block  CC=10  out:10
    _apply_context_metadata  CC=3  out:4
    _apply_conversation_block  CC=1  out:10
    _apply_paths_block  CC=3  out:4
    _apply_process_access_block  CC=4  out:5
    _apply_process_block  CC=9  out:12
    _command_transport  CC=3  out:2
    _parse_access_body  CC=1  out:12
  nlp2dsl_sdk.doql.render  [2 funcs]
    render_doql_context  CC=62  out:129
    write_doql_context  CC=1  out:4
  nlp2dsl_sdk.doql.runtime  [3 funcs]
    context_inline_payload  CC=14  out:18
    load_doql_inline_from_env  CC=2  out:3
    resolve_doql_context_path  CC=1  out:1
  nlp2dsl_sdk.doql_registry  [3 funcs]
    merge_registry_observations  CC=11  out:10
    refresh_doql_registry  CC=10  out:17
    refresh_doql_registry_from_state  CC=1  out:1
  nlp2dsl_sdk.encoding  [7 funcs]
    _apply_utf8_locale_env  CC=2  out:3
    _auto_configure_once  CC=2  out:1
    _explicit_utf8_locale  CC=4  out:2
    _reconfigure_stdio  CC=4  out:2
    _set_utf8_locale  CC=3  out:1
    configure_utf8  CC=3  out:4
    utf8_auto_enabled  CC=1  out:3
  nlp2dsl_sdk.example_bootstrap  [1 funcs]
    ensure_doql_registry  CC=6  out:16
  nlp2dsl_sdk.invoice_pdf  [2 funcs]
    build_invoice_pdf_bytes  CC=3  out:23
    write_invoice_pdf  CC=1  out:4
  nlp2dsl_sdk.invoice_policy  [3 funcs]
    apply_invoice_context  CC=3  out:8
    apply_invoice_policies  CC=5  out:6
    is_invoice_example  CC=2  out:1
  nlp2dsl_sdk.path_resolve  [2 funcs]
    _examples_portable_candidates  CC=8  out:16
    resolve_attachment_path  CC=9  out:19
  nlp2dsl_sdk.preview  [12 funcs]
    ensure_services  CC=5  out:8
    execute_from_text  CC=8  out:15
    execute_text_examples  CC=8  out:9
    execution_payload  CC=3  out:3
    finalize_example_artifacts  CC=2  out:2
    preview_text_examples  CC=9  out:13
    print_execution_result  CC=5  out:11
    print_json  CC=1  out:2
    print_run_context_hints  CC=13  out:20
    print_run_outcome  CC=21  out:40
  nlp2dsl_sdk.process_policy  [11 funcs]
    _as_list  CC=8  out:9
    _deep_merge_process  CC=5  out:7
    _load_nlp2dsl_payload  CC=12  out:12
    _merge_access  CC=5  out:10
    _merge_conversation_from_profile  CC=5  out:4
    _merge_paths  CC=4  out:8
    apply_process_policies  CC=7  out:9
    load_platform_process_defaults  CC=4  out:7
    merge_process_config  CC=4  out:5
    process_policy_from_profile_block  CC=23  out:45
  nlp2dsl_sdk.reflection  [12 funcs]
    _context_queries_from_issues  CC=9  out:4
    _data_lookup  CC=3  out:0
    _entities_from_response  CC=6  out:5
    _intent_from_response  CC=10  out:8
    _missing_vs_target  CC=20  out:18
    _parse_validation_issue  CC=2  out:3
    _resolutions_available  CC=6  out:4
    build_target_plan  CC=20  out:21
    format_reflection_summary  CC=6  out:6
    reflect  CC=9  out:11
  nlp2dsl_sdk.stack_flow  [2 funcs]
    _emit_compose  CC=3  out:8
    bootstrap_registry  CC=1  out:6
  nlp2dsl_sdk.step_validation  [1 funcs]
    validate_step_config_from_map  CC=1  out:1
  nlp2dsl_sdk.system_map_bridge  [3 funcs]
    _command_to_ir  CC=12  out:10
    doql_file_to_system_map  CC=1  out:3
    task_context_to_system_map  CC=24  out:29
  nlp2dsl_sdk.system_map_generator  [4 funcs]
    _bootstrap_system_map  CC=2  out:3
    _parse_llm_json  CC=5  out:8
    build_introspection_payload  CC=11  out:20
    generate_system_map  CC=8  out:15
  nlp2dsl_sdk.system_map_models  [4 funcs]
    _annotation_for_field  CC=11  out:3
    build_command_registry  CC=2  out:1
    command_input_model  CC=4  out:5
    validate_config_against_map  CC=2  out:5
  nlp2dsl_sdk.system_map_render  [1 funcs]
    render_system_map_doql  CC=70  out:164
  nlp2dsl_sdk.system_map_runtimes  [4 funcs]
    _repo_root_from_example  CC=2  out:0
    build_runtimes_for_example  CC=18  out:35
    load_example_profile  CC=7  out:7
    resolve_command_runtime  CC=7  out:3
  nlp2dsl_sdk.validation.helpers  [4 funcs]
    is_empty  CC=3  out:2
    parse_amount  CC=3  out:1
    pdf_amount_mismatch  CC=3  out:5
    pdf_structure_issues  CC=3  out:1
  nlp2dsl_sdk.validation.issue  [1 funcs]
    issues_to_messages  CC=2  out:1
  nlp2dsl_sdk.validation.messages  [1 funcs]
    legacy_message_to_issue  CC=3  out:2
  nlp2dsl_sdk.validation.pipeline  [9 funcs]
    _context_from_map  CC=3  out:5
    validate_dsl_contract_issues  CC=1  out:1
    validate_dsl_contract_messages  CC=1  out:2
    validate_step_config_from_map  CC=2  out:2
    validate_step_config_from_map_issues  CC=2  out:3
    validate_step_issues  CC=1  out:1
    validate_step_messages  CC=1  out:2
    validate_workflow_from_map  CC=2  out:2
    validate_workflow_from_map_issues  CC=9  out:17
  nlp2dsl_sdk.validation.resolutions  [2 funcs]
    _append_plan  CC=2  out:2
    plan_resolutions  CC=17  out:15
  nlp2dsl_sdk.validation.rules.attachment  [3 funcs]
    _resolve_path  CC=2  out:2
    attachment_issues_for_config  CC=3  out:6
    validate_attachment_path  CC=11  out:17
  nlp2dsl_sdk.validation.rules.dsl_contract  [6 funcs]
    _is_non_empty_string  CC=2  out:3
    _issue  CC=1  out:1
    _type_name  CC=2  out:1
    _validate_optional_text_field  CC=5  out:5
    _validate_step  CC=7  out:17
    validate_dsl_contract  CC=6  out:15
  nlp2dsl_sdk.validation.rules.runtime_health  [5 funcs]
    _runtime_field  CC=4  out:5
    probe_health_endpoint  CC=9  out:11
    runtime_id_for_intent  CC=5  out:2
    validate_runtime_health  CC=10  out:8
    validate_runtime_health_for_intent  CC=1  out:2
  nlp2dsl_sdk.validation.rules.step_config  [3 funcs]
    _format_issues  CC=11  out:21
    validate_step  CC=13  out:18
    validate_workflow_steps  CC=4  out:5
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
  backend.app.step_validator.validate_step_config_issues → nlp2dsl_sdk.validation.rules.step_config.validate_step
  backend.app.step_validator.validate_step_config_issues → backend.app.step_validator._validation_context
  backend.app.step_validator.validate_step_config → nlp2dsl_sdk.validation.issue.issues_to_messages
  backend.app.step_validator.validate_step_config → backend.app.step_validator.validate_step_config_issues
  backend.app.workflow_events.WorkflowEventHub.publish → nlp-service.app.settings.SettingsManager.set
  backend.app.workflow_events.WorkflowEventHub.subscriber_count → nlp-service.app.settings.SettingsManager.set
  backend.app.dsl_validation.validate_dsl_for_execution → nlp2dsl_sdk.validation.rules.dsl_contract.validate_dsl_contract
  backend.app.dsl_validation.missing_fields_from_issues → nlp-service.app.settings.SettingsManager.set
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.missing_fields_from_issues
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.format_dsl_validation_message
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.validation_issue_payloads
  backend.app.path_resolve.resolve_attachment_path → backend.app.path_resolve._examples_portable_candidates
  backend.app.routers.system.system_execute → backend.app.logging_setup.get_request_id
  backend.app.routers.testql_compat._maybe_execute_on_message → backend.app.engine.run_workflow
  backend.app.routers.testql_compat.testql_chatstart → backend.app.routers.testql_compat._resolve_text
  backend.app.routers.testql_compat.testql_chatstart → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._resolve_conv_id
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._resolve_text
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._maybe_execute_on_message
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.routers.testql_compat._resolve_conv_id
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.engine.run_workflow
  backend.app.routers.testql_compat.testql_workflow_from_text → backend.app.routers.workflow.workflow_from_text
  backend.app.routers.chat._maybe_auto_execute → backend.app.routers.chat._execute_ready_dsl
  backend.app.routers.chat._maybe_auto_execute → backend.app.routers.chat._execution_requested
  backend.app.routers.chat._execution_requested → backend.app.routers.chat._is_explicit_execute_request
  backend.app.routers.chat._execution_requested → backend.app.routers.chat._is_auto_execute_requested
  backend.app.routers.chat._uses_mullm_backend → backend.app.routers.chat._mullm_steps
  backend.app.routers.chat._prepare_mullm_execution → backend.app.routers.chat._mullm_steps
  backend.app.routers.chat._mark_auto_execute_message → backend.app.routers.chat._is_explicit_execute_request
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

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/wronai/nlp2dsl
# generated in 0.22s
# nodes: 451 | edges: 500 | modules: 107
# CC̄=4.7

HUBS[20]:
  nlp2dsl_sdk.system_map_render.render_system_map_doql
    CC=70  in:5  out:164  total:169
  nlp2dsl_sdk.doql.render.render_doql_context
    CC=62  in:2  out:129  total:131
  nlp2dsl_sdk.compose_generator.generate_stack_compose
    CC=13  in:1  out:79  total:80
  nlp2dsl_sdk.conversation_artifacts.format_transcript
    CC=25  in:1  out:57  total:58
  backend.app.engine._execute_workflow
    CC=13  in:2  out:50  total:52
  packages.nlp2cmd-intent.src.nlp2cmd_intent.keywords.keyword_patterns.KeywordPatterns._load_detector_config_from_json
    CC=33  in:0  out:48  total:48
  nlp2dsl_sdk.preview.print_workflow_preview
    CC=18  in:8  out:38  total:46
  nlp2dsl_sdk.process_policy.process_policy_from_profile_block
    CC=23  in:1  out:45  total:46
  nlp2dsl_sdk.preview.print_run_outcome
    CC=21  in:1  out:40  total:41
  nlp-service.app.settings.SettingsManager.set
    CC=4  in:27  out:11  total:38
  nlp2dsl_sdk.system_map_runtimes.build_runtimes_for_example
    CC=18  in:1  out:35  total:36
  nlp2dsl_sdk.conversation_testql.validate_conversation_scenario
    CC=21  in:1  out:34  total:35
  nlp2dsl_sdk.doql.parse.collect_task_context
    CC=19  in:3  out:32  total:35
  backend.app.path_resolve.resolve_attachment_path
    CC=13  in:9  out:26  total:35
  examples.01-invoice.scenario.run
    CC=20  in:0  out:34  total:34
  nlp2dsl_sdk.doql.parse.load_platform_map
    CC=18  in:1  out:32  total:33
  nlp2dsl_sdk.system_map_bridge.task_context_to_system_map
    CC=24  in:3  out:29  total:32
  nlp2dsl_sdk.doql.parse.enrich_task_context_from_client
    CC=19  in:1  out:29  total:30
  nlp2dsl_sdk.artifacts.build_process_trace
    CC=17  in:1  out:29  total:30
  backend.app.routers.workflow.workflow_from_text
    CC=9  in:1  out:29  total:30

MODULES:
  backend.app.attachment_validation  [1 funcs]
    ensure_attachment_validation  CC=10  out:10
  backend.app.dsl_validation  [5 funcs]
    dsl_validation_response  CC=1  out:3
    format_dsl_validation_message  CC=2  out:4
    missing_fields_from_issues  CC=5  out:3
    validate_dsl_for_execution  CC=1  out:1
    validation_issue_payloads  CC=2  out:1
  backend.app.engine  [7 funcs]
    _execute_workflow  CC=13  out:50
    _persist_workflow_snapshot  CC=2  out:2
    _publish_workflow_event  CC=2  out:2
    _track_background_task  CC=1  out:5
    _workflow_steps_payload  CC=2  out:1
    run_workflow  CC=1  out:2
    start_workflow  CC=1  out:7
  backend.app.logging_setup  [1 funcs]
    get_request_id  CC=1  out:1
  backend.app.path_resolve  [2 funcs]
    _examples_portable_candidates  CC=8  out:16
    resolve_attachment_path  CC=13  out:26
  backend.app.routers.chat  [19 funcs]
    _doql_context_path  CC=2  out:2
    _dsl_steps  CC=4  out:2
    _execute_ready_dsl  CC=5  out:16
    _execution_observation_from_dsl  CC=4  out:4
    _execution_requested  CC=2  out:2
    _is_auto_execute_requested  CC=3  out:4
    _is_explicit_execute_request  CC=2  out:4
    _mark_auto_execute_message  CC=6  out:9
    _maybe_auto_execute  CC=3  out:3
    _merge_attachment_validation  CC=9  out:7
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
  backend.app.routers.testql_compat  [8 funcs]
    _alias_response  CC=3  out:1
    _maybe_execute_on_message  CC=6  out:13
    _resolve_conv_id  CC=3  out:2
    _resolve_text  CC=8  out:8
    testql_chatmessage  CC=4  out:10
    testql_chatstart  CC=5  out:9
    testql_runworkflow  CC=4  out:17
    testql_workflow_from_text  CC=1  out:2
  backend.app.routers.workflow  [6 funcs]
    _format_sse  CC=5  out:6
    _workflow_snapshot  CC=1  out:7
    run_workflow_endpoint  CC=1  out:2
    start_workflow_endpoint  CC=1  out:2
    stream_workflow  CC=2  out:22
    workflow_from_text  CC=9  out:29
  backend.app.step_validator  [3 funcs]
    _validation_context  CC=1  out:5
    validate_step_config  CC=1  out:2
    validate_step_config_issues  CC=2  out:3
  backend.app.workflow_events  [2 funcs]
    publish  CC=2  out:4
    subscriber_count  CC=1  out:3
  examples.01-invoice.scenario  [4 funcs]
    _attachment_validation  CC=9  out:9
    _example_dir  CC=1  out:2
    _run_autonomous  CC=1  out:9
    run  CC=20  out:34
  examples.02-email.scenario  [1 funcs]
    run  CC=7  out:19
  examples.03-report-and-notify.scenario  [1 funcs]
    run  CC=6  out:17
  examples.04-scheduled-report.scenario  [1 funcs]
    run  CC=11  out:21
  examples.05-conversation-flow.scenario  [4 funcs]
    _save_conversation_artifacts  CC=1  out:2
    run  CC=2  out:2
    run_demo  CC=2  out:18
    run_interactive  CC=1  out:2
  examples.06-interactive-chat.scenario  [3 funcs]
    run  CC=2  out:2
    run_demo  CC=4  out:15
    run_interactive  CC=1  out:4
  examples.07-email-conversation.scenario  [1 funcs]
    run  CC=3  out:15
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
  examples.13-autonomous-invoice-stack.scenario  [1 funcs]
    run  CC=20  out:24
  examples.bootstrap  [1 funcs]
    bootstrap  CC=11  out:16
  examples.code_generation_examples  [1 funcs]
    main  CC=1  out:1
  nlp-service.app.audio_parser  [4 funcs]
    send_audio  CC=2  out:2
    is_stt_available  CC=2  out:0
    stt_audio  CC=9  out:14
    stt_file  CC=2  out:4
  nlp-service.app.conversation.attachment_gate  [1 funcs]
    workflow_needs_attachment  CC=8  out:4
  nlp-service.app.conversation.autonomous_loop  [6 funcs]
    _attachment_valid_ok  CC=7  out:7
    _example_dir  CC=3  out:5
    _maybe_delete_generated_attachment  CC=5  out:5
    _resolve_artifact_file  CC=7  out:13
    _step_config_for_validation  CC=4  out:2
    _try_fixture_attachment  CC=16  out:20
  nlp-service.app.conversation.doql_autofill  [2 funcs]
    _resolve_attachment_path  CC=1  out:2
    load_context_for_state  CC=8  out:5
  nlp-service.app.conversation.doql_registry  [7 funcs]
    _entities_to_data  CC=5  out:4
    _format_value  CC=4  out:5
    _patch_doql_file  CC=5  out:16
    _render_block  CC=2  out:5
    _try_sdk_refresh  CC=4  out:7
    refresh_registry_for_state  CC=16  out:21
    reload_context_after_refresh  CC=1  out:2
  nlp-service.app.conversation.invoice_policy  [2 funcs]
    invoice_attachment_policy_active  CC=9  out:2
    is_invoice_example  CC=2  out:1
  nlp-service.app.conversation.merge  [1 funcs]
    merge_into_state  CC=13  out:4
  nlp-service.app.conversation.orchestrator  [3 funcs]
    continue_conversation  CC=4  out:13
    get_conversation  CC=2  out:3
    start_conversation  CC=4  out:12
  nlp-service.app.conversation.runtime_gate  [2 funcs]
    process_scope_blocked  CC=12  out:7
    runtime_unavailable_message  CC=7  out:2
  nlp-service.app.conversation.system_map  [3 funcs]
    get_doql_context  CC=1  out:1
    runtime_id_for_action  CC=2  out:2
    set_doql_context  CC=1  out:1
  nlp-service.app.dsl.forms  [1 funcs]
    get_action_form  CC=5  out:12
  nlp-service.app.dsl.pipeline  [1 funcs]
    map_to_dsl_with_enrichment  CC=6  out:4
  nlp-service.app.execution.delegate  [3 funcs]
    execution_backend_for_intent  CC=5  out:4
    execution_backend_for_runtime  CC=4  out:0
    is_delegated_to_mullm  CC=2  out:1
  nlp-service.app.governance.config  [2 funcs]
    get_access_config  CC=1  out:1
    reload_access_config  CC=1  out:1
  nlp-service.app.governance.policy  [1 funcs]
    authorize_action  CC=5  out:8
  nlp-service.app.main  [16 funcs]
    _parse_context_json  CC=5  out:3
    _run_parser  CC=3  out:3
    access_check  CC=3  out:6
    access_config  CC=3  out:12
    access_reload  CC=2  out:2
    action_schema  CC=2  out:3
    actions_schema  CC=3  out:3
    chat_message  CC=6  out:15
    chat_start  CC=7  out:15
    chat_state  CC=2  out:4
  nlp-service.app.registry  [1 funcs]
    get_trigger  CC=3  out:2
  nlp-service.app.request_context  [1 funcs]
    get_example_dir  CC=2  out:3
  nlp-service.app.routing.observability  [1 funcs]
    routing_metrics_snapshot  CC=1  out:1
  nlp-service.app.routing.orientation  [1 funcs]
    orient_query  CC=16  out:27
  nlp-service.app.routing.parser.llm  [1 funcs]
    _detect_provider  CC=10  out:8
  nlp-service.app.routing.parser.resolve_mode  [1 funcs]
    parse_with_mode  CC=11  out:12
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
  nlp2dsl_sdk.__main__  [1 funcs]
    main  CC=5  out:10
  nlp2dsl_sdk.artifact_layout  [9 funcs]
    artifact_root  CC=1  out:2
    current_run_id  CC=2  out:4
    ensure_layout  CC=1  out:6
    resolve_registry_path  CC=9  out:11
    run_dir  CC=2  out:4
    write_last_run_report  CC=1  out:6
    write_reflection_snapshot  CC=1  out:8
    write_registry  CC=2  out:5
    write_turn_snapshot  CC=4  out:21
  nlp2dsl_sdk.artifacts  [14 funcs]
    __init__  CC=5  out:6
    finalize  CC=5  out:13
    record  CC=1  out:6
    _extract_actions  CC=4  out:5
    _mask_secret  CC=3  out:1
    _slugify  CC=2  out:5
    build_process_trace  CC=17  out:29
    collect_environment  CC=6  out:4
    example_artifact_root  CC=1  out:2
    get_example_writer  CC=2  out:4
  nlp2dsl_sdk.attachment_validation  [6 funcs]
    _apply_attachment_to_execution  CC=7  out:6
    _attachment_from_dsl  CC=8  out:10
    _prefer_local_validation  CC=4  out:2
    build_attachment_validation  CC=8  out:15
    enrich_chat_response  CC=11  out:12
    format_attachment_validation  CC=10  out:8
  nlp2dsl_sdk.autonomous_flow  [1 funcs]
    _start_with_extra  CC=6  out:22
  nlp2dsl_sdk.cli  [12 funcs]
    _actions  CC=3  out:8
    _analyze  CC=2  out:1
    _chat_start  CC=2  out:10
    _client  CC=1  out:1
    _demo  CC=6  out:5
    _detect_example_dir  CC=4  out:4
    _display  CC=13  out:27
    _health  CC=2  out:6
    _run  CC=5  out:9
    _run_with_doql  CC=6  out:12
  nlp2dsl_sdk.client  [18 funcs]
    _handle_completed_response  CC=14  out:22
    _persist_reflection  CC=11  out:18
    _print_attachment_validation  CC=3  out:3
    _record_turn  CC=1  out:2
    _reflect_executed_turn  CC=5  out:10
    _refresh_doql_registry  CC=13  out:15
    save_artifacts  CC=2  out:4
    start  CC=2  out:12
    chat_message  CC=6  out:11
    chat_start  CC=4  out:10
  nlp2dsl_sdk.compose_generator  [10 funcs]
    _default_deploy  CC=1  out:2
    _default_generated_services  CC=2  out:2
    _default_schedules  CC=1  out:1
    _run_process_docker_script  CC=1  out:1
    _run_process_host_script  CC=1  out:1
    _run_script_content  CC=2  out:3
    _stack_compose_dict  CC=8  out:10
    _wait_for_backend_shell  CC=1  out:1
    enrich_ir_for_stack  CC=5  out:5
    generate_stack_compose  CC=13  out:79
  nlp2dsl_sdk.conversation_artifacts  [3 funcs]
    _routing_summary  CC=6  out:4
    format_transcript  CC=25  out:57
    write_conversation_artifacts  CC=1  out:13
  nlp2dsl_sdk.conversation_testql  [3 funcs]
    _is_nlp_kind  CC=1  out:2
    dry_run_conversation_scenario  CC=1  out:1
    validate_conversation_scenario  CC=21  out:34
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
  nlp2dsl_sdk.doql.parse  [23 funcs]
    _append_collection_blocks  CC=10  out:15
    _apply_capabilities_block  CC=5  out:7
    _apply_context_block  CC=10  out:10
    _apply_context_metadata  CC=3  out:4
    _apply_conversation_block  CC=1  out:10
    _apply_paths_block  CC=3  out:4
    _apply_process_access_block  CC=4  out:5
    _apply_process_block  CC=9  out:12
    _command_transport  CC=3  out:2
    _parse_access_body  CC=1  out:12
  nlp2dsl_sdk.doql.render  [2 funcs]
    render_doql_context  CC=62  out:129
    write_doql_context  CC=1  out:4
  nlp2dsl_sdk.doql.runtime  [3 funcs]
    context_inline_payload  CC=14  out:18
    load_doql_inline_from_env  CC=2  out:3
    resolve_doql_context_path  CC=1  out:1
  nlp2dsl_sdk.doql_registry  [3 funcs]
    merge_registry_observations  CC=11  out:10
    refresh_doql_registry  CC=10  out:17
    refresh_doql_registry_from_state  CC=1  out:1
  nlp2dsl_sdk.encoding  [7 funcs]
    _apply_utf8_locale_env  CC=2  out:3
    _auto_configure_once  CC=2  out:1
    _explicit_utf8_locale  CC=4  out:2
    _reconfigure_stdio  CC=4  out:2
    _set_utf8_locale  CC=3  out:1
    configure_utf8  CC=3  out:4
    utf8_auto_enabled  CC=1  out:3
  nlp2dsl_sdk.example_bootstrap  [1 funcs]
    ensure_doql_registry  CC=6  out:16
  nlp2dsl_sdk.invoice_pdf  [2 funcs]
    build_invoice_pdf_bytes  CC=3  out:23
    write_invoice_pdf  CC=1  out:4
  nlp2dsl_sdk.invoice_policy  [3 funcs]
    apply_invoice_context  CC=3  out:8
    apply_invoice_policies  CC=5  out:6
    is_invoice_example  CC=2  out:1
  nlp2dsl_sdk.path_resolve  [2 funcs]
    _examples_portable_candidates  CC=8  out:16
    resolve_attachment_path  CC=9  out:19
  nlp2dsl_sdk.preview  [12 funcs]
    ensure_services  CC=5  out:8
    execute_from_text  CC=8  out:15
    execute_text_examples  CC=8  out:9
    execution_payload  CC=3  out:3
    finalize_example_artifacts  CC=2  out:2
    preview_text_examples  CC=9  out:13
    print_execution_result  CC=5  out:11
    print_json  CC=1  out:2
    print_run_context_hints  CC=13  out:20
    print_run_outcome  CC=21  out:40
  nlp2dsl_sdk.process_policy  [11 funcs]
    _as_list  CC=8  out:9
    _deep_merge_process  CC=5  out:7
    _load_nlp2dsl_payload  CC=12  out:12
    _merge_access  CC=5  out:10
    _merge_conversation_from_profile  CC=5  out:4
    _merge_paths  CC=4  out:8
    apply_process_policies  CC=7  out:9
    load_platform_process_defaults  CC=4  out:7
    merge_process_config  CC=4  out:5
    process_policy_from_profile_block  CC=23  out:45
  nlp2dsl_sdk.reflection  [12 funcs]
    _context_queries_from_issues  CC=9  out:4
    _data_lookup  CC=3  out:0
    _entities_from_response  CC=6  out:5
    _intent_from_response  CC=10  out:8
    _missing_vs_target  CC=20  out:18
    _parse_validation_issue  CC=2  out:3
    _resolutions_available  CC=6  out:4
    build_target_plan  CC=20  out:21
    format_reflection_summary  CC=6  out:6
    reflect  CC=9  out:11
  nlp2dsl_sdk.stack_flow  [2 funcs]
    _emit_compose  CC=3  out:8
    bootstrap_registry  CC=1  out:6
  nlp2dsl_sdk.step_validation  [1 funcs]
    validate_step_config_from_map  CC=1  out:1
  nlp2dsl_sdk.system_map_bridge  [3 funcs]
    _command_to_ir  CC=12  out:10
    doql_file_to_system_map  CC=1  out:3
    task_context_to_system_map  CC=24  out:29
  nlp2dsl_sdk.system_map_generator  [4 funcs]
    _bootstrap_system_map  CC=2  out:3
    _parse_llm_json  CC=5  out:8
    build_introspection_payload  CC=11  out:20
    generate_system_map  CC=8  out:15
  nlp2dsl_sdk.system_map_models  [4 funcs]
    _annotation_for_field  CC=11  out:3
    build_command_registry  CC=2  out:1
    command_input_model  CC=4  out:5
    validate_config_against_map  CC=2  out:5
  nlp2dsl_sdk.system_map_render  [1 funcs]
    render_system_map_doql  CC=70  out:164
  nlp2dsl_sdk.system_map_runtimes  [4 funcs]
    _repo_root_from_example  CC=2  out:0
    build_runtimes_for_example  CC=18  out:35
    load_example_profile  CC=7  out:7
    resolve_command_runtime  CC=7  out:3
  nlp2dsl_sdk.validation.helpers  [4 funcs]
    is_empty  CC=3  out:2
    parse_amount  CC=3  out:1
    pdf_amount_mismatch  CC=3  out:5
    pdf_structure_issues  CC=3  out:1
  nlp2dsl_sdk.validation.issue  [1 funcs]
    issues_to_messages  CC=2  out:1
  nlp2dsl_sdk.validation.messages  [1 funcs]
    legacy_message_to_issue  CC=3  out:2
  nlp2dsl_sdk.validation.pipeline  [9 funcs]
    _context_from_map  CC=3  out:5
    validate_dsl_contract_issues  CC=1  out:1
    validate_dsl_contract_messages  CC=1  out:2
    validate_step_config_from_map  CC=2  out:2
    validate_step_config_from_map_issues  CC=2  out:3
    validate_step_issues  CC=1  out:1
    validate_step_messages  CC=1  out:2
    validate_workflow_from_map  CC=2  out:2
    validate_workflow_from_map_issues  CC=9  out:17
  nlp2dsl_sdk.validation.resolutions  [2 funcs]
    _append_plan  CC=2  out:2
    plan_resolutions  CC=17  out:15
  nlp2dsl_sdk.validation.rules.attachment  [3 funcs]
    _resolve_path  CC=2  out:2
    attachment_issues_for_config  CC=3  out:6
    validate_attachment_path  CC=11  out:17
  nlp2dsl_sdk.validation.rules.dsl_contract  [6 funcs]
    _is_non_empty_string  CC=2  out:3
    _issue  CC=1  out:1
    _type_name  CC=2  out:1
    _validate_optional_text_field  CC=5  out:5
    _validate_step  CC=7  out:17
    validate_dsl_contract  CC=6  out:15
  nlp2dsl_sdk.validation.rules.runtime_health  [5 funcs]
    _runtime_field  CC=4  out:5
    probe_health_endpoint  CC=9  out:11
    runtime_id_for_intent  CC=5  out:2
    validate_runtime_health  CC=10  out:8
    validate_runtime_health_for_intent  CC=1  out:2
  nlp2dsl_sdk.validation.rules.step_config  [3 funcs]
    _format_issues  CC=11  out:21
    validate_step  CC=13  out:18
    validate_workflow_steps  CC=4  out:5
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
  backend.app.step_validator.validate_step_config_issues → nlp2dsl_sdk.validation.rules.step_config.validate_step
  backend.app.step_validator.validate_step_config_issues → backend.app.step_validator._validation_context
  backend.app.step_validator.validate_step_config → nlp2dsl_sdk.validation.issue.issues_to_messages
  backend.app.step_validator.validate_step_config → backend.app.step_validator.validate_step_config_issues
  backend.app.workflow_events.WorkflowEventHub.publish → nlp-service.app.settings.SettingsManager.set
  backend.app.workflow_events.WorkflowEventHub.subscriber_count → nlp-service.app.settings.SettingsManager.set
  backend.app.dsl_validation.validate_dsl_for_execution → nlp2dsl_sdk.validation.rules.dsl_contract.validate_dsl_contract
  backend.app.dsl_validation.missing_fields_from_issues → nlp-service.app.settings.SettingsManager.set
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.missing_fields_from_issues
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.format_dsl_validation_message
  backend.app.dsl_validation.dsl_validation_response → backend.app.dsl_validation.validation_issue_payloads
  backend.app.path_resolve.resolve_attachment_path → backend.app.path_resolve._examples_portable_candidates
  backend.app.routers.system.system_execute → backend.app.logging_setup.get_request_id
  backend.app.routers.testql_compat._maybe_execute_on_message → backend.app.engine.run_workflow
  backend.app.routers.testql_compat.testql_chatstart → backend.app.routers.testql_compat._resolve_text
  backend.app.routers.testql_compat.testql_chatstart → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._resolve_conv_id
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._resolve_text
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_chatmessage → backend.app.routers.testql_compat._maybe_execute_on_message
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.routers.testql_compat._resolve_conv_id
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.routers.testql_compat._alias_response
  backend.app.routers.testql_compat.testql_runworkflow → backend.app.engine.run_workflow
  backend.app.routers.testql_compat.testql_workflow_from_text → backend.app.routers.workflow.workflow_from_text
  backend.app.routers.chat._maybe_auto_execute → backend.app.routers.chat._execute_ready_dsl
  backend.app.routers.chat._maybe_auto_execute → backend.app.routers.chat._execution_requested
  backend.app.routers.chat._execution_requested → backend.app.routers.chat._is_explicit_execute_request
  backend.app.routers.chat._execution_requested → backend.app.routers.chat._is_auto_execute_requested
  backend.app.routers.chat._uses_mullm_backend → backend.app.routers.chat._mullm_steps
  backend.app.routers.chat._prepare_mullm_execution → backend.app.routers.chat._mullm_steps
  backend.app.routers.chat._mark_auto_execute_message → backend.app.routers.chat._is_explicit_execute_request
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 287f 39021L | python:213,json:19,shell:12,yaml:10,toml:10,txt:6,yml:3,rust:2,javascript:2,ini:1 | 2026-06-06
# generated in 0.06s
# CC̅=4.7 | critical:50/998 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    _load_patterns_from_json CC=19 (limit:15)
  🟡 CC    _load_detector_config_from_json CC=33 (limit:15)
  🟡 CC    detect CC=17 (limit:15)
  🟡 CC    _fast_path_detection CC=73 (limit:15)
  🟡 CC    _keyword_detection CC=15 (limit:15)
  🟡 CC    build_process_trace CC=17 (limit:15)
  🟡 CC    build_runtimes_for_example CC=18 (limit:15)
  🟡 CC    merge_execution_observation CC=17 (limit:15)
  🟡 CC    format_transcript CC=25 (limit:15)
  🟡 CC    task_context_to_system_map CC=24 (limit:15)
  🟡 CC    build_target_plan CC=20 (limit:15)
  🟡 CC    _missing_vs_target CC=20 (limit:15)
  🟡 CC    validate_conversation_scenario CC=21 (limit:15)
  🟡 CC    print_run_outcome CC=21 (limit:15)
  🟡 CC    print_workflow_preview CC=18 (limit:15)
  🟡 CC    process_policy_from_profile_block CC=23 (limit:15)
  🟡 CC    render_system_map_doql CC=70 (limit:15)
  🟡 CC    plan_resolutions CC=17 (limit:15)
  🟡 CC    autofill_entities CC=15 (limit:15)
  🟡 CC    render_doql_context CC=62 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[379]:
  [1] Src [main]: main
      PURITY: 100% pure
  [2] Src [main]: main
      PURITY: 100% pure
  [3] Src [server]: server
      PURITY: 100% pure
  [4] Src [npmCommand]: npmCommand
      PURITY: 100% pure
  [5] Src [child]: child
      PURITY: 100% pure
  [6] Src [shuttingDown]: shuttingDown
      PURITY: 100% pure
  [7] Src [exitCode]: exitCode → main → shutdown
      PURITY: 100% pure
  [8] Src [http]: http
      PURITY: 100% pure
  [9] Src [fs]: fs
      PURITY: 100% pure
  [10] Src [path]: path
      PURITY: 100% pure
  [11] Src [HOST]: HOST
      PURITY: 100% pure
  [12] Src [PORT]: PORT
      PURITY: 100% pure
  [13] Src [ROOT_DIR]: ROOT_DIR
      PURITY: 100% pure
  [14] Src [MIME_TYPES]: MIME_TYPES
      PURITY: 100% pure
  [15] Src [safePath]: safePath
      PURITY: 100% pure
  [16] Src [candidate]: candidate
      PURITY: 100% pure
  [17] Src [fileContents]: fileContents → contentType
      PURITY: 100% pure
  [18] Src [pathname]: pathname
      PURITY: 100% pure
  [19] Src [targetPath]: targetPath
      PURITY: 100% pure
  [20] Src [startServer]: startServer → handleRequest → resolveRequestPath → isInsideRoot
      PURITY: 100% pure
  [21] Src [server]: server → handleRequest → resolveRequestPath → isInsideRoot
      PURITY: 100% pure
  [22] Src [__init__]: __init__
      PURITY: 100% pure
  [23] Src [format]: format
      PURITY: 100% pure
  [24] Src [__init__]: __init__
      PURITY: 100% pure
  [25] Src [dispatch]: dispatch
      PURITY: 100% pure
  [26] Src [setup_logging]: setup_logging
      PURITY: 100% pure
  [27] Src [to_dict]: to_dict
      PURITY: 100% pure
  [28] Src [__init__]: __init__
      PURITY: 100% pure
  [29] Src [subscribe]: subscribe
      PURITY: 100% pure
  [30] Src [unsubscribe]: unsubscribe
      PURITY: 100% pure
  [31] Src [publish]: publish → set → _coerce_type
      PURITY: 100% pure
  [32] Src [subscriber_count]: subscriber_count → set → _coerce_type
      PURITY: 100% pure
  [33] Src [health]: health
      PURITY: 100% pure
  [34] Src [__init__]: __init__
      PURITY: 100% pure
  [35] Src [save_run]: save_run
      PURITY: 100% pure
  [36] Src [get_run]: get_run
      PURITY: 100% pure
  [37] Src [list_runs]: list_runs
      PURITY: 100% pure
  [38] Src [count_runs]: count_runs
      PURITY: 100% pure
  [39] Src [create_workflow_repo]: create_workflow_repo
      PURITY: 100% pure
  [40] Src [to_dict]: to_dict
      PURITY: 100% pure
  [41] Src [__init__]: __init__
      PURITY: 100% pure
  [42] Src [_ensure_engine]: _ensure_engine
      PURITY: 100% pure
  [43] Src [_get_session_factory]: _get_session_factory
      PURITY: 100% pure
  [44] Src [_ensure_tables]: _ensure_tables
      PURITY: 100% pure
  [45] Src [save_run]: save_run
      PURITY: 100% pure
  [46] Src [update_run_status]: update_run_status
      PURITY: 100% pure
  [47] Src [get_run]: get_run
      PURITY: 100% pure
  [48] Src [list_runs]: list_runs
      PURITY: 100% pure
  [49] Src [count_runs]: count_runs
      PURITY: 100% pure
  [50] Src [close]: close
      PURITY: 100% pure

LAYERS:
  scripts/                        CC̄=8.5    ←in:0  →out:9  !! split
  │ !! run-example-testql-results   524L  2C   14m  CC=23     ←0
  │ !! run-example-docker-e2e     320L  0C   12m  CC=28     ←0
  │ !! run-conversation-scenario   260L  0C    8m  CC=36     ←0
  │ !! run-execution-scenario     184L  0C    8m  CC=18     ←0
  │ aggregate-example-testql    49L  0C    1m  CC=7      ←0
  │ publish-all.sh              44L  0C    1m  CC=0.0    ←0
  │ setup-dev.sh                43L  0C    0m  CC=0.0    ←0
  │ bootstrap-venv.sh           31L  0C    0m  CC=0.0    ←0
  │ _dotenv                     23L  0C    1m  CC=9      ←1
  │
  examples/                       CC̄=6.3    ←in:0  →out:3
  │ !! testql-results.json       1980L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780668530.json   642L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780673613.json   636L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780734808.json   636L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780694039.json   636L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780672619.json   636L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780737026.json   636L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669461.json   322L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669469.json   322L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668482.json   321L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668555.json   320L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669486.json   319L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668647.json   319L  0C    0m  CC=0.0    ←0
  │ example-profiles.yaml      178L  0C    0m  CC=0.0    ←0
  │ benchmark_queries          158L  1C    0m  CC=0.0    ←0
  │ !! scenario                   137L  0C    4m  CC=16     ←1
  │ !! scenario                    92L  0C    4m  CC=20     ←0
  │ scenario                    88L  0C    2m  CC=13     ←0
  │ docker-e2e-results.json     86L  0C    0m  CC=0.0    ←0
  │ run-all.sh                  70L  0C    0m  CC=0.0    ←0
  │ !! scenario                    68L  0C    2m  CC=20     ←0
  │ scenario                    60L  0C    1m  CC=11     ←0
  │ scenario                    59L  0C    1m  CC=6      ←0
  │ docker-compose.yml          58L  0C    0m  CC=0.0    ←0
  │ scenario                    57L  0C    1m  CC=7      ←0
  │ scenario                    55L  0C    3m  CC=4      ←0
  │ scenario                    51L  0C    4m  CC=2      ←0
  │ scenario                    49L  0C    1m  CC=8      ←0
  │ bootstrap                   47L  0C    1m  CC=11     ←0
  │ scenario                    44L  0C    1m  CC=9      ←0
  │ scenario                    44L  0C    1m  CC=3      ←0
  │ scenario                    37L  0C    1m  CC=3      ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ main                        33L  0C    0m  CC=0.0    ←0
  │ code_generation_examples    25L  0C    1m  CC=1      ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ stack-request.txt            8L  0C    0m  CC=0.0    ←0
  │ run.sh                       6L  0C    0m  CC=0.0    ←0
  │ invoice-request.txt          4L  0C    0m  CC=0.0    ←0
  │ requirements.txt             1L  0C    0m  CC=0.0    ←0
  │
  nlp2dsl_sdk/                    CC̄=5.2    ←in:60  →out:33  !! split
  │ !! client                     893L  2C   60m  CC=14     ←0
  │ !! compose_generator          512L  1C   16m  CC=13     ←1
  │ !! parse                      466L  0C   24m  CC=19     ←10
  │ !! artifacts                  432L  1C   17m  CC=17     ←10
  │ demos                      355L  1C   11m  CC=6      ←3
  │ !! reflection                 346L  4C   12m  CC=20     ←3
  │ !! preview                    336L  0C   13m  CC=21     ←17
  │ !! process_policy             290L  0C   13m  CC=23     ←4
  │ cli                        269L  0C   13m  CC=13     ←0
  │ system_map_ir              264L  16C    4m  CC=7      ←0
  │ !! system_map_render          244L  0C    1m  CC=70     ←4
  │ stack_flow                 231L  3C    6m  CC=10     ←0
  │ !! system_map_bridge          223L  0C    5m  CC=24     ←5
  │ system_map_generator       202L  0C    5m  CC=11     ←3
  │ !! render                     196L  0C    2m  CC=62     ←2
  │ !! doql_registry              189L  0C    5m  CC=17     ←4
  │ !! system_map_runtimes        174L  0C    4m  CC=18     ←5
  │ artifact_layout            170L  0C   10m  CC=9      ←9
  │ messages                   169L  0C   14m  CC=6      ←1
  │ dsl_contract               166L  0C    6m  CC=7      ←2
  │ step_config                162L  0C    3m  CC=13     ←6
  │ !! resolutions                155L  2C    3m  CC=17     ←1
  │ runtime_health             136L  0C    5m  CC=10     ←3
  │ models                     131L  7C    4m  CC=6      ←0
  │ attachment_validation      130L  0C    6m  CC=11     ←3
  │ pipeline                   126L  0C    9m  CC=9      ←0
  │ attachment                 115L  0C    3m  CC=11     ←3
  │ !! conversation_artifacts     113L  0C    3m  CC=25     ←5
  │ autonomous_flow            105L  1C    5m  CC=8      ←0
  │ !! runtime                    105L  0C    4m  CC=15     ←11
  │ !! conversation_testql        103L  1C    4m  CC=21     ←1
  │ encoding                    92L  0C    8m  CC=4      ←5
  │ invoice_pdf                 75L  0C    3m  CC=3      ←2
  │ issue                       61L  2C    3m  CC=8      ←5
  │ path_resolve                56L  0C    2m  CC=9      ←0
  │ __init__                    54L  0C    1m  CC=3      ←0
  │ example_bootstrap           53L  0C    1m  CC=6      ←2
  │ invoice_policy              52L  0C    3m  CC=5      ←3
  │ doql_context                50L  0C    0m  CC=0.0    ←0
  │ system_map_models           48L  0C    4m  CC=11     ←0
  │ context                     48L  1C    1m  CC=3      ←0
  │ __init__                    46L  0C    1m  CC=2      ←0
  │ __init__                    46L  0C    0m  CC=0.0    ←0
  │ __main__                    45L  0C    1m  CC=5      ←0
  │ step_validation             43L  0C    2m  CC=1      ←1
  │ example_loader              39L  0C    1m  CC=7      ←0
  │ helpers                     36L  0C    4m  CC=3      ←4
  │
  packages/                       CC̄=4.7    ←in:0  →out:0
  │ !! patterns.json             2016L  0C    0m  CC=0.0    ←0
  │ !! keyword_detector          1209L  2C   22m  CC=73     ←0
  │ !! keyword_patterns           228L  1C   15m  CC=33     ←0
  │ keyword_intent_detector_config.json   215L  0C    0m  CC=0.0    ←0
  │ runner                     194L  2C   11m  CC=8      ←0
  │ executor                   155L  1C    6m  CC=10     ←0
  │ adapter                    134L  0C    8m  CC=12     ←2
  │ cli                         91L  0C    3m  CC=7      ←0
  │ rest_workflow               82L  1C    2m  CC=7      ←0
  │ rule_shell                  74L  1C    3m  CC=10     ←0
  │ data_files                  67L  0C    4m  CC=6      ←0
  │ execution_plan              59L  2C    1m  CC=1      ←0
  │ facade                      54L  3C    6m  CC=4      ←0
  │ workflow_backend            50L  0C    4m  CC=4      ←1
  │ nlp2cmd_convert             47L  0C    1m  CC=10     ←2
  │ intent                      44L  3C    2m  CC=2      ←0
  │ encoding                    44L  0C    0m  CC=0.0    ←0
  │ domain_mapping              43L  0C    2m  CC=7      ←1
  │ clarification               37L  1C    3m  CC=4      ←1
  │ router                      36L  2C    3m  CC=3      ←0
  │ input                       34L  0C    1m  CC=3      ←2
  │ target_kind                 34L  2C    0m  CC=0.0    ←0
  │ pyproject.toml              34L  0C    0m  CC=0.0    ←0
  │ __init__                    31L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              28L  0C    0m  CC=0.0    ←0
  │ install-dev.sh              25L  0C    1m  CC=0.0    ←0
  │ pipeline                    24L  1C    2m  CC=3      ←0
  │ pyproject.toml              24L  0C    0m  CC=0.0    ←0
  │ cli                         22L  0C    1m  CC=1      ←0
  │ __init__                    17L  0C    0m  CC=0.0    ←0
  │ normalize                   16L  1C    1m  CC=2      ←0
  │ __init__                    16L  0C    0m  CC=0.0    ←0
  │ protocols                   15L  2C    2m  CC=1      ←0
  │ strategy                    15L  1C    2m  CC=1      ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │
  nlp-service/                    CC̄=4.5    ←in:0  →out:0
  │ !! main                       645L  0C   26m  CC=14     ←1
  │ !! rules                      564L  0C   31m  CC=21     ←2
  │ registry                   421L  0C    5m  CC=5      ←5
  │ !! orientation                379L  1C   11m  CC=16     ←2
  │ !! responses                  368L  0C   19m  CC=25     ←3
  │ policy                     302L  2C   14m  CC=5      ←2
  │ !! autonomous_loop            299L  1C   12m  CC=21     ←1
  │ code_generator             279L  1C    8m  CC=14     ←0
  │ !! orchestrator               265L  0C   12m  CC=16     ←1
  │ settings                   251L  6C   11m  CC=6      ←20
  │ !! mapper                     244L  0C    7m  CC=23     ←1
  │ !! resolve                    196L  0C    6m  CC=18     ←1
  │ !! doql_registry              176L  0C    7m  CC=16     ←3
  │ config                     165L  1C   13m  CC=8      ←4
  │ schemas                    150L  12C    0m  CC=0.0    ←0
  │ enrich                     149L  0C    4m  CC=14     ←1
  │ audio_parser               148L  1C    8m  CC=9      ←1
  │ !! doql_context               147L  0C    3m  CC=20     ←1
  │ llm                        145L  0C    3m  CC=10     ←3
  │ native                     143L  0C   13m  CC=6      ←1
  │ reflection                 137L  0C    9m  CC=10     ←1
  │ !! doql_autofill              135L  0C    4m  CC=20     ←7
  │ process_agent              116L  0C    3m  CC=9      ←1
  │ system_map                 110L  0C   12m  CC=6      ←11
  │ step_validator             109L  1C    9m  CC=9      ←1
  │ logging_setup              100L  2C    6m  CC=3      ←0
  │ forms                       91L  0C    1m  CC=5      ←2
  │ runtime_gate                89L  0C    3m  CC=12     ←1
  │ path_resolve                87L  0C    2m  CC=14     ←0
  │ path_policy                 83L  0C    5m  CC=6      ←2
  │ prompt_catalog              82L  0C    1m  CC=8      ←0
  │ bootstrap                   78L  0C    3m  CC=14     ←0
  │ invoice_pdf                 73L  0C    3m  CC=3      ←0
  │ !! attachment_validation       72L  0C    1m  CC=16     ←0
  │ invoice_paths               70L  0C    4m  CC=9      ←1
  │ registry                    66L  0C    0m  CC=0.0    ←0
  │ loader                      62L  0C    3m  CC=5      ←1
  │ config                      60L  1C    0m  CC=0.0    ←0
  │ redis_store                 58L  1C    7m  CC=3      ←0
  │ observability               57L  0C    3m  CC=7      ←2
  │ intent                      55L  1C    2m  CC=3      ←0
  │ resolve_mode                53L  0C    1m  CC=11     ←2
  │ pyproject.toml              53L  0C    0m  CC=0.0    ←0
  │ delegate                    48L  0C    5m  CC=5      ←1
  │ factory                     46L  0C    1m  CC=4      ←2
  │ merge                       36L  0C    1m  CC=13     ←1
  │ system_executor             35L  0C   13m  CC=12     ←1
  │ pipeline                    31L  0C    1m  CC=6      ←4
  │ __init__                    30L  1C    4m  CC=1      ←0
  │ manifest.json               30L  0C    0m  CC=0.0    ←0
  │ invoice_policy              27L  0C    2m  CC=9      ←3
  │ attachment_gate             25L  0C    1m  CC=8      ←2
  │ request_context             23L  0C    2m  CC=3      ←5
  │ memory                      23L  1C    5m  CC=1      ←0
  │ __init__                    21L  0C    1m  CC=2      ←0
  │ orchestrator                21L  0C    0m  CC=0.0    ←0
  │ facade                      20L  0C    1m  CC=3      ←0
  │ __init__                    17L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  15L  0C    0m  CC=0.0    ←0
  │ parser_enrich               15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                    14L  0C    0m  CC=0.0    ←0
  │ requirements.txt            10L  0C    0m  CC=0.0    ←0
  │ parser_rules                 5L  0C    0m  CC=0.0    ←0
  │ parser_llm                   5L  0C    0m  CC=0.0    ←0
  │ mapper                       5L  0C    0m  CC=0.0    ←0
  │ facade                       5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     4L  0C    0m  CC=0.0    ←0
  │ uri_match                    3L  0C    3m  CC=8      ←1
  │ native                       3L  0C    0m  CC=0.0    ←0
  │ config                       3L  0C    0m  CC=0.0    ←0
  │ bootstrap                    3L  0C    0m  CC=0.0    ←0
  │ policy                       3L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │
  backend/                        CC̄=2.9    ←in:0  →out:0
  │ engine                     307L  0C    7m  CC=13     ←3
  │ chat                       250L  0C   19m  CC=9      ←0
  │ workflow                   203L  0C   10m  CC=9      ←1
  │ postgres                   172L  3C   11m  CC=4      ←0
  │ testql_compat              153L  3C    8m  CC=8      ←0
  │ attachment_validation      109L  0C    6m  CC=11     ←1
  │ logging_setup              100L  2C    6m  CC=3      ←5
  │ workflow_events             91L  2C    6m  CC=3      ←0
  │ settings                    81L  0C    7m  CC=2      ←0
  │ path_resolve                64L  0C    2m  CC=13     ←8
  │ schemas                     64L  6C    0m  CC=0.0    ←0
  │ step_validator              60L  0C    3m  CC=2      ←5
  │ pyproject.toml              52L  0C    0m  CC=0.0    ←0
  │ main                        50L  0C    1m  CC=1      ←0
  │ __init__                    49L  1C    6m  CC=2      ←0
  │ dsl_validation              47L  0C    5m  CC=5      ←2
  │ config                      42L  1C    0m  CC=0.0    ←0
  │ memory                      37L  1C    6m  CC=2      ←0
  │ system                      29L  0C    1m  CC=2      ←0
  │ workflow                    22L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  14L  0C    0m  CC=0.0    ←0
  │ requirements.txt             9L  0C    0m  CC=0.0    ←0
  │ pytest.ini                   5L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  tauri-wrapper/                  CC̄=2.7    ←in:0  →out:0
  │ serve-dist.js              139L  0C   21m  CC=8      ←0
  │ desktop.sh                  79L  0C    0m  CC=0.0    ←0
  │ dev.js                      56L  0C    7m  CC=11     ←0
  │ tauri.conf.json             43L  0C    0m  CC=0.0    ←0
  │ package.json                18L  0C    0m  CC=0.0    ←0
  │ Cargo.toml                  17L  0C    0m  CC=0.0    ←0
  │ main.rs                      7L  0C    1m  CC=2      ←0
  │ build.rs                     3L  0C    1m  CC=1      ←0
  │
  worker/                         CC̄=2.3    ←in:0  →out:5
  │ worker                     271L  0C   14m  CC=5      ←0
  │ logging_setup              100L  2C    6m  CC=3      ←0
  │ attachment_validation       63L  0C    2m  CC=8      ←1
  │ pyproject.toml              46L  0C    0m  CC=0.0    ←0
  │ config                      27L  1C    0m  CC=0.0    ←0
  │ Dockerfile                  14L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ requirements.txt             4L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1319L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  512L  0C    0m  CC=0.0    ←0
  │ nlp2dsl.yaml               204L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml         130L  0C    0m  CC=0.0    ←0
  │ Makefile                   102L  0C    0m  CC=0.0    ←0
  │ run-all-tests.sh            90L  0C    3m  CC=0.0    ←0
  │ prefact.yaml                82L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              75L  0C    0m  CC=0.0    ←0
  │ project.sh                  59L  0C    0m  CC=0.0    ←0
  │ metrun-profile.sh           48L  0C    0m  CC=0.0    ←0
  │ docker-compose.e2e.yml      41L  0C    0m  CC=0.0    ←0
  │ pyqual.yaml                 41L  0C    0m  CC=0.0    ←0
  │ .pfix-test-wrapper.sh       16L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-examples.testql.toon.yaml   428L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml   128L  0C    0m  CC=0.0    ←0
  │ generated-api-smoke.testql.toon.yaml    39L  0C    0m  CC=0.0    ←0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     backend/app/__init__.py                   0L

COUPLING:
                                                     nlp2dsl_sdk                 nlp-service.app                nlp2dsl_sdk.doql          nlp2dsl_sdk.validation                     backend.app                         scripts         packages.nlp2cmd-intent             examples.01-invoice    examples.04-scheduled-report                          worker               examples.02-email   examples.03-report-and-notify             examples.12-ir-show                        examples  examples.07-email-conversation
                     nlp2dsl_sdk                              ──                               6                              20                               4                               2                              ←5                               1                              ←6                              ←5                              ←1                              ←4                              ←4                              ←4                              ←3                              ←3  hub
                 nlp-service.app                               8                              ──                              13                              10                               8                              ←2                              ←5                                                                                                                                                                                                                                                                  hub
                nlp2dsl_sdk.doql                               2                               1                              ──                               1                                                              ←2                                                                                                                                                                                                                                                                                                  hub
          nlp2dsl_sdk.validation                              ←4                               2                              ←1                              ──                               1                                                                                                                                                              ←3                                                                                                                                                                  hub
                     backend.app                              ←2                               3                                                               3                              ──                                                                                                                                                              ←1                                                                                                                                                                  hub
                         scripts                               5                               2                               2                                                                                              ──                                                                                                                                                                                                                                                                                                  !! fan-out
         packages.nlp2cmd-intent                              ←1                               5                                                                                                                                                              ──                                                                                                                                                                                                                                                                
             examples.01-invoice                               6                                                                                                                                                                                                                              ──                                                                                                                                                                                                                                
    examples.04-scheduled-report                               5                                                                                                                                                                                                                                                              ──                                                                                                                                                                                                
                          worker                               1                                                                                               3                               1                                                                                                                                                              ──                                                                                                                                                                
               examples.02-email                               4                                                                                                                                                                                                                                                                                                                              ──                                                                                                                                
   examples.03-report-and-notify                               4                                                                                                                                                                                                                                                                                                                                                              ──                                                                                                
             examples.12-ir-show                               4                                                                                                                                                                                                                                                                                                                                                                                              ──                                                                
                        examples                               3                                                                                                                                                                                                                                                                                                                                                                                                                              ──                                
  examples.07-email-conversation                               3                                                                                                                                                                                                                                                                                                                                                                                                                                                              ──
  CYCLES: none
  HUB: nlp2dsl_sdk.validation/ (fan-in=21)
  HUB: nlp-service.app/ (fan-in=20)
  HUB: nlp2dsl_sdk/ (fan-in=60)
  HUB: backend.app/ (fan-in=12)
  HUB: nlp2dsl_sdk.doql/ (fan-in=35)
  SMELL: scripts/ fan-out=9 → split needed
  SMELL: nlp-service.app/ fan-out=40 → split needed
  SMELL: nlp2dsl_sdk/ fan-out=33 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 23 groups | 216f 23931L | 2026-06-06

SUMMARY:
  files_scanned: 216
  total_lines:   23931
  dup_groups:    23
  dup_fragments: 56
  saved_lines:   378
  scan_ms:       3699

HOTSPOTS[7] (files with most duplication):
  nlp2dsl_sdk/invoice_pdf.py  dup=65L  groups=3  frags=3  (0.3%)
  nlp-service/app/validation/invoice_pdf.py  dup=63L  groups=3  frags=3  (0.3%)
  worker/invoice_pdf.py  dup=63L  groups=3  frags=3  (0.3%)
  backend/app/logging_setup.py  dup=49L  groups=5  frags=5  (0.2%)
  nlp-service/app/logging_setup.py  dup=49L  groups=5  frags=5  (0.2%)
  worker/logging_setup.py  dup=49L  groups=5  frags=5  (0.2%)
  scripts/run-example-docker-e2e.py  dup=45L  groups=1  frags=2  (0.2%)

DUPLICATES[23] (ranked by impact):
  [2efbb7dcb6fc1905] ! EXAC  build_invoice_pdf_bytes  L=49 N=3 saved=98 sim=1.00
      nlp-service/app/validation/invoice_pdf.py:12-60  (build_invoice_pdf_bytes)
      nlp2dsl_sdk/invoice_pdf.py:12-61  (build_invoice_pdf_bytes)
      worker/invoice_pdf.py:12-60  (build_invoice_pdf_bytes)
  [5980042b45ef9ea3] ! STRU  setup_logging  L=22 N=3 saved=44 sim=1.00
      backend/app/logging_setup.py:79-100  (setup_logging)
      nlp-service/app/logging_setup.py:79-100  (setup_logging)
      worker/logging_setup.py:79-100  (setup_logging)
  [a58ac04d8adce867]   EXAC  format  L=12 N=3 saved=24 sim=1.00
      backend/app/logging_setup.py:40-51  (format)
      nlp-service/app/logging_setup.py:40-51  (format)
      worker/logging_setup.py:40-51  (format)
  [505c25b135c0d048]   EXAC  write_invoice_pdf  L=11 N=3 saved=22 sim=1.00
      nlp-service/app/validation/invoice_pdf.py:63-73  (write_invoice_pdf)
      nlp2dsl_sdk/invoice_pdf.py:64-75  (write_invoice_pdf)
      worker/invoice_pdf.py:63-73  (write_invoice_pdf)
  [d54d4c265bf6ceca]   STRU  run_execution  L=22 N=2 saved=22 sim=1.00
      scripts/run-example-docker-e2e.py:99-120  (run_execution)
      scripts/run-example-docker-e2e.py:123-145  (run_conversation)
  [8d8164856e051e29]   STRU  _process_shell_dockerfile  L=10 N=3 saved=20 sim=1.00
      nlp2dsl_sdk/compose_generator.py:176-185  (_process_shell_dockerfile)
      nlp2dsl_sdk/compose_generator.py:188-198  (_cron_sidecar_dockerfile)
      nlp2dsl_sdk/compose_generator.py:311-320  (_runner_dockerfile)
  [6c27c009f67df952]   EXAC  _examples_portable_candidates  L=19 N=2 saved=19 sim=1.00
      backend/app/path_resolve.py:9-27  (_examples_portable_candidates)
      nlp2dsl_sdk/path_resolve.py:9-27  (_examples_portable_candidates)
  [ffd95d6b2707ba43]   EXAC  dispatch  L=9 N=3 saved=18 sim=1.00
      backend/app/logging_setup.py:68-76  (dispatch)
      nlp-service/app/logging_setup.py:68-76  (dispatch)
      worker/logging_setup.py:68-76  (dispatch)
  [11197122b4458ed5]   EXAC  _wait_health  L=12 N=2 saved=12 sim=1.00
      scripts/run-conversation-scenario.py:25-36  (_wait_health)
      scripts/run-execution-scenario.py:25-36  (_wait_health)
  [7f9ec2529df6c8b0]   STRU  chat_start  L=11 N=2 saved=11 sim=1.00
      backend/app/routers/chat.py:215-225  (chat_start)
      backend/app/routers/chat.py:229-240  (chat_message)
  [fe1a465464777068]   STRU  handle_notify_slack  L=11 N=2 saved=11 sim=1.00
      worker/worker.py:160-170  (handle_notify_slack)
      worker/worker.py:174-184  (handle_notify_telegram)
  [566b50b29fefe2fb]   STRU  _attachment_from_dsl  L=10 N=2 saved=10 sim=1.00
      backend/app/attachment_validation.py:67-76  (_attachment_from_dsl)
      nlp2dsl_sdk/attachment_validation.py:69-78  (_attachment_from_dsl)
  [cdcb9de5af04411d]   STRU  _missing_required_issue  L=10 N=2 saved=10 sim=1.00
      nlp2dsl_sdk/validation/messages.py:22-31  (_missing_required_issue)
      nlp2dsl_sdk/validation/messages.py:34-43  (_quality_missing_issue)
  [8e33482aef8974e1]   STRU  action_schema  L=7 N=2 saved=7 sim=1.00
      backend/app/routers/settings.py:29-35  (action_schema)
      backend/app/routers/settings.py:47-53  (get_settings_section)
  [8aa06fa5f1348ed4]   STRU  _execute_keyword_in_text  L=7 N=2 saved=7 sim=1.00
      nlp-service/app/conversation/responses.py:56-62  (_execute_keyword_in_text)
      nlp-service/app/routing/parser/rules.py:240-246  (_alias_in_text)
  [e2bd3c5d1f7d650b]   EXAC  __init__  L=3 N=3 saved=6 sim=1.00
      backend/app/logging_setup.py:36-38  (__init__)
      nlp-service/app/logging_setup.py:36-38  (__init__)
      worker/logging_setup.py:36-38  (__init__)
  [2283cb9d4d16ec25]   EXAC  __init__  L=3 N=3 saved=6 sim=1.00
      backend/app/logging_setup.py:64-66  (__init__)
      nlp-service/app/logging_setup.py:64-66  (__init__)
      worker/logging_setup.py:64-66  (__init__)
  [cc5120287255aec8]   EXAC  add  L=3 N=3 saved=6 sim=1.00
      nlp-service/app/validation/invoice_pdf.py:31-33  (add)
      nlp2dsl_sdk/invoice_pdf.py:32-34  (add)
      worker/invoice_pdf.py:31-33  (add)
  [8af82767bfb2b892]   STRU  run_workflow_endpoint  L=3 N=3 saved=6 sim=1.00
      backend/app/routers/workflow.py:78-80  (run_workflow_endpoint)
      backend/app/routers/workflow.py:84-86  (start_workflow_endpoint)
      nlp-service/app/main.py:96-101  (parse_text)
  [d8abcb97f9e3aea3]   STRU  _extract_report_type  L=6 N=2 saved=6 sim=1.00
      nlp-service/app/routing/parser/rules.py:424-429  (_extract_report_type)
      nlp-service/app/routing/parser/rules.py:432-437  (_extract_format)
  [2ce1096adac6d1a4]   STRU  actions_schema  L=5 N=2 saved=5 sim=1.00
      backend/app/routers/settings.py:21-25  (actions_schema)
      backend/app/routers/settings.py:39-43  (get_settings)
  [642bdda11ce23f85]   EXAC  _repo_root_from_example  L=4 N=2 saved=4 sim=1.00
      nlp2dsl_sdk/doql/parse.py:253-256  (_repo_root_from_example)
      nlp2dsl_sdk/system_map_runtimes.py:31-34  (_repo_root_from_example)
  [88c3564ed3834adc]   STRU  _extract_file_path_entity  L=4 N=2 saved=4 sim=1.00
      nlp-service/app/routing/parser/rules.py:502-505  (_extract_file_path_entity)
      nlp-service/app/routing/parser/rules.py:508-511  (_extract_setting_path_entity)

REFACTOR[23] (ranked by priority):
  [1] ◐ extract_function   → utils/build_invoice_pdf_bytes.py
      WHY: 3 occurrences of 49-line block across 3 files — saves 98 lines
      FILES: nlp-service/app/validation/invoice_pdf.py, nlp2dsl_sdk/invoice_pdf.py, worker/invoice_pdf.py
  [2] ● extract_function   → utils/setup_logging.py
      WHY: 3 occurrences of 22-line block across 3 files — saves 44 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [3] ● extract_class      → utils/format.py
      WHY: 3 occurrences of 12-line block across 3 files — saves 24 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [4] ● extract_function   → utils/write_invoice_pdf.py
      WHY: 3 occurrences of 11-line block across 3 files — saves 22 lines
      FILES: nlp-service/app/validation/invoice_pdf.py, nlp2dsl_sdk/invoice_pdf.py, worker/invoice_pdf.py
  [5] ○ extract_function   → scripts/utils/run_execution.py
      WHY: 2 occurrences of 22-line block across 1 files — saves 22 lines
      FILES: scripts/run-example-docker-e2e.py
  [6] ○ extract_function   → nlp2dsl_sdk/utils/_process_shell_dockerfile.py
      WHY: 3 occurrences of 10-line block across 1 files — saves 20 lines
      FILES: nlp2dsl_sdk/compose_generator.py
  [7] ○ extract_function   → utils/_examples_portable_candidates.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: backend/app/path_resolve.py, nlp2dsl_sdk/path_resolve.py
  [8] ● extract_class      → utils/dispatch.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [9] ○ extract_function   → scripts/utils/_wait_health.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: scripts/run-conversation-scenario.py, scripts/run-execution-scenario.py
  [10] ○ extract_function   → backend/app/routers/utils/chat_start.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: backend/app/routers/chat.py
  [11] ○ extract_function   → worker/utils/handle_notify_slack.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: worker/worker.py
  [12] ○ extract_function   → utils/_attachment_from_dsl.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: backend/app/attachment_validation.py, nlp2dsl_sdk/attachment_validation.py
  [13] ○ extract_function   → nlp2dsl_sdk/validation/utils/_missing_required_issue.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: nlp2dsl_sdk/validation/messages.py
  [14] ○ extract_function   → backend/app/routers/utils/action_schema.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: backend/app/routers/settings.py
  [15] ○ extract_function   → nlp-service/app/utils/_execute_keyword_in_text.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: nlp-service/app/conversation/responses.py, nlp-service/app/routing/parser/rules.py
  [16] ● extract_class      → utils/__init__.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [17] ● extract_class      → utils/__init__.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [18] ● extract_function   → utils/add.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: nlp-service/app/validation/invoice_pdf.py, nlp2dsl_sdk/invoice_pdf.py, worker/invoice_pdf.py
  [19] ○ extract_function   → utils/run_workflow_endpoint.py
      WHY: 3 occurrences of 3-line block across 2 files — saves 6 lines
      FILES: backend/app/routers/workflow.py, nlp-service/app/main.py
  [20] ○ extract_function   → nlp-service/app/routing/parser/utils/_extract_report_type.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: nlp-service/app/routing/parser/rules.py
  [21] ○ extract_function   → backend/app/routers/utils/actions_schema.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: backend/app/routers/settings.py
  [22] ○ extract_function   → nlp2dsl_sdk/utils/_repo_root_from_example.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: nlp2dsl_sdk/doql/parse.py, nlp2dsl_sdk/system_map_runtimes.py
  [23] ○ extract_function   → nlp-service/app/routing/parser/utils/_extract_file_path_entity.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: nlp-service/app/routing/parser/rules.py

QUICK_WINS[12] (low risk, high savings — do first):
  [5] extract_function   saved=22L  → scripts/utils/run_execution.py
      FILES: run-example-docker-e2e.py
  [6] extract_function   saved=20L  → nlp2dsl_sdk/utils/_process_shell_dockerfile.py
      FILES: compose_generator.py
  [7] extract_function   saved=19L  → utils/_examples_portable_candidates.py
      FILES: path_resolve.py, path_resolve.py
  [9] extract_function   saved=12L  → scripts/utils/_wait_health.py
      FILES: run-conversation-scenario.py, run-execution-scenario.py
  [10] extract_function   saved=11L  → backend/app/routers/utils/chat_start.py
      FILES: chat.py
  [11] extract_function   saved=11L  → worker/utils/handle_notify_slack.py
      FILES: worker.py
  [12] extract_function   saved=10L  → utils/_attachment_from_dsl.py
      FILES: attachment_validation.py, attachment_validation.py
  [13] extract_function   saved=10L  → nlp2dsl_sdk/validation/utils/_missing_required_issue.py
      FILES: messages.py
  [14] extract_function   saved=7L  → backend/app/routers/utils/action_schema.py
      FILES: settings.py
  [15] extract_function   saved=7L  → nlp-service/app/utils/_execute_keyword_in_text.py
      FILES: responses.py, rules.py

DEPENDENCY_RISK[11] (duplicates spanning multiple packages):
  build_invoice_pdf_bytes  packages=3  files=3
      nlp-service/app/validation/invoice_pdf.py
      nlp2dsl_sdk/invoice_pdf.py
      worker/invoice_pdf.py
  setup_logging  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
  format  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
  write_invoice_pdf  packages=3  files=3
      nlp-service/app/validation/invoice_pdf.py
      nlp2dsl_sdk/invoice_pdf.py
      worker/invoice_pdf.py
  dispatch  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
  __init__  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
  __init__  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py

EFFORT_ESTIMATE (total ≈ 24.5h):
  hard   build_invoice_pdf_bytes             saved=98L  ~588min
  hard   setup_logging                       saved=44L  ~176min
  hard   format                              saved=24L  ~96min
  medium write_invoice_pdf                   saved=22L  ~88min
  medium run_execution                       saved=22L  ~44min
  medium _process_shell_dockerfile           saved=20L  ~40min
  medium _examples_portable_candidates       saved=19L  ~76min
  medium dispatch                            saved=18L  ~72min
  easy   _wait_health                        saved=12L  ~24min
  easy   chat_start                          saved=11L  ~22min
  ... +13 more (~244min)

METRICS-TARGET:
  dup_groups:  23 → 0
  saved_lines: 378 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 897 func | 143f | 2026-06-06
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py
      WHY: 1209L, 2 classes, max CC=73
      EFFORT: ~4h  IMPACT: 88257

  [2] !! SPLIT-FUNC      KeywordIntentDetector._fast_path_detection  CC=73  fan=29
      WHY: CC=73 exceeds 15
      EFFORT: ~1h  IMPACT: 2117

  [3] !! SPLIT-FUNC      render_system_map_doql  CC=70  fan=15
      WHY: CC=70 exceeds 15
      EFFORT: ~1h  IMPACT: 1050

  [4] !! SPLIT-FUNC      render_doql_context  CC=62  fan=11
      WHY: CC=62 exceeds 15
      EFFORT: ~1h  IMPACT: 682

  [5] !! SPLIT-FUNC      KeywordPatterns._load_detector_config_from_json  CC=33  fan=18
      WHY: CC=33 exceeds 15
      EFFORT: ~1h  IMPACT: 594

  [6] !! SPLIT-FUNC      build_and_check_dsl  CC=25  fan=23
      WHY: CC=25 exceeds 15
      EFFORT: ~1h  IMPACT: 575

  [7] !  SPLIT-FUNC      collect_task_context  CC=19  fan=26
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 494

  [8] !  SPLIT-FUNC      autonomous_resolve_turn  CC=21  fan=23
      WHY: CC=21 exceeds 15
      EFFORT: ~1h  IMPACT: 483

  [9] !  SPLIT-FUNC      task_context_to_system_map  CC=24  fan=20
      WHY: CC=24 exceeds 15
      EFFORT: ~1h  IMPACT: 480

  [10] !! SPLIT-FUNC      format_transcript  CC=25  fan=17
      WHY: CC=25 exceeds 15
      EFFORT: ~1h  IMPACT: 425


RISKS[3]:
  ⚠ Splitting packages/nlp2cmd-intent/src/nlp2cmd_intent/data/patterns.json may break 0 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths
  ⚠ Splitting packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py may break 22 import paths

METRICS-TARGET:
  CC̄:          4.5 → ≤3.1
  max-CC:      73 → ≤20
  god-modules: 8 → 0
  high-CC(≥15): 38 → ≤19
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=4.6 → now CC̄=4.5
```

### Validation (`project/validation.toon.yaml`)

```toon markpact:analysis path=project/validation.toon.yaml
# vallm batch | 170f | 69✓ 3⚠ 38✗ | 2026-04-08

SUMMARY:
  scanned: 170  passed: 69 (40.6%)  warnings: 3  errors: 38  unsupported: 63

WARNINGS[3]{path,score}:
  nlp2dsl_sdk/client.py,0.96
    issues[3]{rule,severity,message,line}:
      complexity.cyclomatic,warning,_handle_response has cyclomatic complexity 16 (max: 15),475
      complexity.maintainability,warning,Low maintainability index: 17.6 (threshold: 20),
      complexity.lizard_cc,warning,_handle_response: CC=16 exceeds limit 15,475
  nlp2dsl_sdk/demos.py,0.96
    issues[3]{rule,severity,message,line}:
      complexity.cyclomatic,warning,run_code_generation_demo has cyclomatic complexity 20 (max: 15),540
      complexity.maintainability,warning,Low maintainability index: 17.4 (threshold: 20),
      complexity.lizard_cc,warning,run_code_generation_demo: CC=20 exceeds limit 15,540
  tests/test_nlp2dsl_sdk.py,0.96
    issues[2]{rule,severity,message,line}:
      complexity.cyclomatic,warning,test_workflow_and_conversation_endpoints has cyclomatic complexity 17 (max: 15),74
      complexity.cyclomatic,warning,test_code_generation_methods_hit_expected_services has cyclomatic complexity 16 (max: 15),205

ERRORS[38]{path,score}:
  backend/app/workflow.py,0.57
    issues[5]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.engine' not found,12
      python.import.resolvable,error,Module 'app.engine' not found,13
      python.import.resolvable,error,Module 'app.engine' not found,14
      python.import.resolvable,error,Module 'app.engine' not found,15
      python.import.resolvable,error,Module 'app.routers.workflow' not found,16
  nlp-service/app/store/memory.py,0.57
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.store' not found,5
  tests/tests/test_tests.py,0.57
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'tests' not found,11
  backend/tests/test_config.py,0.61
    issues[10]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,16
      python.import.resolvable,error,Module 'app.config' not found,22
      python.import.resolvable,error,Module 'app.config' not found,28
      python.import.resolvable,error,Module 'app.config' not found,34
      python.import.resolvable,error,Module 'app.config' not found,44
      python.import.resolvable,error,Module 'app.config' not found,50
      python.import.resolvable,error,Module 'app.config' not found,56
      python.import.resolvable,error,Module 'app.config' not found,62
      python.import.resolvable,error,Module 'app.config' not found,71
      python.import.resolvable,error,Module 'app.engine' not found,80
  nlp-service/tests/test_system_executor.py,0.62
    issues[15]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.registry' not found,11
      python.import.resolvable,error,Module 'app.settings' not found,12
      python.import.resolvable,error,Module 'app.system_executor' not found,13
      python.import.resolvable,error,Module 'app.system_executor' not found,231
      python.import.resolvable,error,Module 'app.system_executor' not found,248
      python.import.resolvable,error,Module 'app.system_executor' not found,262
      python.import.resolvable,error,Module 'app.system_executor' not found,279
      python.import.resolvable,error,Module 'app.system_executor' not found,291
      python.import.resolvable,error,Module 'app.system_executor' not found,305
      python.import.resolvable,error,Module 'app.system_executor' not found,324
      python.import.resolvable,error,Module 'app.system_executor' not found,352
      python.import.resolvable,error,Module 'app.system_executor' not found,361
      python.import.resolvable,error,Module 'app.system_executor' not found,375
      python.import.resolvable,error,Module 'app.system_executor' not found,389
      python.import.resolvable,error,Module 'app.system_executor' not found,396
  nlp-service/app/store/factory.py,0.66
    issues[4]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.store' not found,14
      python.import.resolvable,error,Module 'app.store.memory' not found,15
      python.import.resolvable,error,Module 'app.config' not found,28
      python.import.resolvable,error,Module 'app.store.redis_store' not found,36
  backend/app/db/__init__.py,0.68
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,42
      python.import.resolvable,error,Module 'app.db.memory' not found,48
      python.import.resolvable,error,Module 'app.db.postgres' not found,46
  backend/app/db/postgres.py,0.68
    issues[6]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'sqlalchemy' not found,11
      python.import.resolvable,error,Module 'sqlalchemy.dialects.postgresql' not found,12
      python.import.resolvable,error,Module 'sqlalchemy.dialects.postgresql' not found,13
      python.import.resolvable,error,Module 'sqlalchemy.ext.asyncio' not found,14
      python.import.resolvable,error,Module 'sqlalchemy.orm' not found,15
      python.import.resolvable,error,Module 'app.db' not found,17
  nlp-service/tests/test_store.py,0.69
    issues[5]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.schemas' not found,11
      python.import.resolvable,error,Module 'app.store.memory' not found,12
      python.import.resolvable,error,Module 'app.store.factory' not found,137
      python.import.resolvable,error,Module 'app.store.factory' not found,150
      python.import.resolvable,error,Module 'app.store.factory' not found,164
  nlp-service/app/mapper.py,0.71
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.registry' not found,13
      python.import.resolvable,error,Module 'app.schemas' not found,20
  nlp-service/app/orchestrator.py,0.71
    issues[6]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.mapper' not found,17
      python.import.resolvable,error,Module 'app.parser_rules' not found,18
      python.import.resolvable,error,Module 'app.registry' not found,19
      python.import.resolvable,error,Module 'app.schemas' not found,20
      python.import.resolvable,error,Module 'app.store.factory' not found,29
      python.import.resolvable,error,Module 'app.system_executor' not found,190
  nlp-service/tests/test_orchestrator.py,0.71
    issues[4]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.orchestrator' not found,11
      python.import.resolvable,error,Module 'app.schemas' not found,18
      python.import.resolvable,error,Module 'app.store.memory' not found,25
      python.import.resolvable,error,Module 'app.orchestrator' not found,31
  nlp-service/app/main.py,0.72
    issues[13]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.audio_parser' not found,32
      python.import.resolvable,error,Module 'app.code_generator' not found,33
      python.import.resolvable,error,Module 'app.config' not found,34
      python.import.resolvable,error,Module 'app.logging_setup' not found,35
      python.import.resolvable,error,Module 'app.mapper' not found,36
      python.import.resolvable,error,Module 'app.orchestrator' not found,37
      python.import.resolvable,error,Module 'app.parser_llm' not found,43
      python.import.resolvable,error,Module 'app.parser_rules' not found,44
      python.import.resolvable,error,Module 'app.registry' not found,45
      python.import.resolvable,error,Module 'app.schemas' not found,46
      python.import.resolvable,error,Module 'app.settings' not found,53
      python.import.resolvable,error,Module 'app.store.factory' not found,54
      python.import.resolvable,error,Module 'app.system_executor' not found,55
  backend/app/main.py,0.73
    issues[5]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.logging_setup' not found,14
      python.import.resolvable,error,Module 'app.routers.chat' not found,15
      python.import.resolvable,error,Module 'app.routers.settings' not found,16
      python.import.resolvable,error,Module 'app.routers.system' not found,17
      python.import.resolvable,error,Module 'app.routers.workflow' not found,18
  backend/tests/test_persistence.py,0.74
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.db.memory' not found,11
      python.import.resolvable,error,Module 'app.db' not found,169
      python.import.resolvable,error,Module 'app.db' not found,182
  nlp-service/tests/test_mapper.py,0.74
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.mapper' not found,10
      python.import.resolvable,error,Module 'app.registry' not found,11
      python.import.resolvable,error,Module 'app.schemas' not found,12
  nlp-service/tests/test_parser_rules.py,0.74
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.parser_rules' not found,10
      python.import.resolvable,error,Module 'app.schemas' not found,11
      python.import.resolvable,error,Module 'app.registry' not found,198
  backend/app/db/memory.py,0.79
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.db' not found,7
  nlp-service/app/parser_rules.py,0.79
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.registry' not found,15
      python.import.resolvable,error,Module 'app.schemas' not found,20
  backend/tests/test_logging.py,0.80
    issues[6]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.logging_setup' not found,18
      python.import.resolvable,error,Module 'app.logging_setup' not found,36
      python.import.resolvable,error,Module 'app.logging_setup' not found,55
      python.import.resolvable,error,Module 'app.logging_setup' not found,72
      python.import.resolvable,error,Module 'app.logging_setup' not found,110
      python.import.resolvable,error,Module 'app.logging_setup' not found,119
  backend/app/engine.py,0.82
    issues[5]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,16
      python.import.resolvable,error,Module 'app.db' not found,17
      python.import.resolvable,error,Module 'app.logging_setup' not found,18
      python.import.resolvable,error,Module 'app.workflow_events' not found,19
      python.import.resolvable,error,Module 'app.schemas' not found,20
  backend/app/routers/chat.py,0.82
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.engine' not found,13
      python.import.resolvable,error,Module 'app.logging_setup' not found,14
      python.import.resolvable,error,Module 'app.schemas' not found,15
  nlp-service/app/store/redis_store.py,0.83
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'redis.asyncio' not found,13
      python.import.resolvable,error,Module 'app.store' not found,15
  nlp-service/app/system_executor.py,0.83
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.registry' not found,16
      python.import.resolvable,error,Module 'app.settings' not found,17
  backend/app/routers/settings.py,0.86
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.engine' not found,13
      python.import.resolvable,error,Module 'app.logging_setup' not found,14
  backend/app/routers/system.py,0.86
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.engine' not found,13
      python.import.resolvable,error,Module 'app.logging_setup' not found,14
  backend/app/routers/workflow.py,0.86
    issues[4]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.engine' not found,15
      python.import.resolvable,error,Module 'app.logging_setup' not found,16
      python.import.resolvable,error,Module 'app.workflow_events' not found,17
      python.import.resolvable,error,Module 'app.schemas' not found,18
  nlp-service/app/audio_parser.py,0.86
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,19
  nlp-service/tests/test_registry.py,0.86
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.registry' not found,10
  test_code_generation.py,0.86
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'code_generator' not found,14
  tests/e2e/test_websocket.py,0.88
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'websockets' not found,17
      python.import.resolvable,error,Module 'websockets.connection' not found,18
  tests/e2e/test_chat_ui.py,0.89
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'playwright.async_api' not found,24
  nlp-service/app/parser_llm.py,0.93
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.schemas' not found,31
  nlp-service/app/settings.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,20
  backend/app/logging_setup.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,87
  nlp-service/app/logging_setup.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'app.config' not found,87
  worker/logging_setup.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'config' not found,87
  worker/worker.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'logging_setup' not found,25

UNSUPPORTED[6]{bucket,count}:
  *.md,25
  Dockerfile*,8
  *.txt,10
  *.yml,2
  *.example,6
  other,12
```

## Intent

Reusable Python SDK for the NLP2DSL platform
