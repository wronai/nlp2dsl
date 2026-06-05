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
- **version**: `0.0.18`
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

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

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

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 208f 23911L | python:144,json:14,shell:11,toml:10,yaml:9,txt:4,yml:2,rust:2,javascript:2,ini:1 | 2026-06-05
# generated in 0.04s
# CC̅=3.6 | critical:13/594 | dups:0 | cycles:0

HEALTH[13]:
  🟡 CC    _load_patterns_from_json CC=19 (limit:15)
  🟡 CC    _load_detector_config_from_json CC=33 (limit:15)
  🟡 CC    detect CC=17 (limit:15)
  🟡 CC    _fast_path_detection CC=73 (limit:15)
  🟡 CC    _keyword_detection CC=15 (limit:15)
  🟡 CC    build_process_trace CC=17 (limit:15)
  🟡 CC    run_benchmark CC=16 (limit:15)
  🟡 CC    _resolve_file_list_host_command CC=15 (limit:15)
  🟡 CC    orient_query CC=16 (limit:15)
  🟡 CC    resolve_intent CC=18 (limit:15)
  🟡 CC    parse_rules CC=15 (limit:15)
  🟡 CC    _apply_context_filters CC=21 (limit:15)
  🟡 CC    _build_config CC=19 (limit:15)

REFACTOR[1]:
  1. split 13 high-CC methods  (CC>15)

PIPELINES[301]:
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
  examples/                       CC̄=5.5    ←in:0  →out:2
  │ !! benchmark_1780668530.json   642L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780672619.json   636L  0C    0m  CC=0.0    ←0
  │ !! benchmark_1780673613.json   636L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669461.json   322L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669469.json   322L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668482.json   321L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668555.json   320L  0C    0m  CC=0.0    ←0
  │ benchmark_1780669486.json   319L  0C    0m  CC=0.0    ←0
  │ benchmark_1780668647.json   319L  0C    0m  CC=0.0    ←0
  │ benchmark_queries          158L  1C    0m  CC=0.0    ←0
  │ !! scenario                   137L  0C    4m  CC=16     ←1
  │ scenario                    88L  0C    2m  CC=13     ←0
  │ scenario                    60L  0C    1m  CC=11     ←0
  │ docker-compose.yml          60L  0C    0m  CC=0.0    ←0
  │ scenario                    58L  0C    1m  CC=6      ←0
  │ scenario                    57L  0C    1m  CC=7      ←0
  │ run-all.sh                  53L  0C    0m  CC=0.0    ←0
  │ scenario                    49L  0C    1m  CC=8      ←0
  │ scenario                    48L  0C    1m  CC=7      ←0
  │ scenario                    45L  0C    3m  CC=3      ←0
  │ scenario                    44L  0C    1m  CC=9      ←0
  │ scenario                    44L  0C    3m  CC=2      ←0
  │ scenario                    37L  0C    1m  CC=3      ←0
  │ scenario                    36L  0C    1m  CC=3      ←0
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
  │ bootstrap                   26L  0C    1m  CC=3      ←0
  │ code_generation_examples    25L  0C    1m  CC=1      ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  23L  0C    0m  CC=0.0    ←0
  │ run.sh                       6L  0C    0m  CC=0.0    ←0
  │ requirements.txt             1L  0C    0m  CC=0.0    ←0
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
  nlp-service/                    CC̄=3.9    ←in:0  →out:0
  │ !! main                       570L  0C   24m  CC=10     ←1
  │ !! rules                      564L  0C   31m  CC=21     ←2
  │ registry                   403L  0C    5m  CC=5      ←4
  │ !! orientation                379L  1C   11m  CC=16     ←2
  │ policy                     302L  2C   14m  CC=5      ←2
  │ responses                  282L  0C   19m  CC=7      ←1
  │ code_generator             279L  1C    8m  CC=14     ←0
  │ settings                   251L  6C   11m  CC=6      ←8
  │ !! mapper                     236L  0C    7m  CC=19     ←1
  │ !! resolve                    194L  0C    6m  CC=18     ←1
  │ config                     165L  1C   13m  CC=8      ←4
  │ audio_parser               148L  1C    8m  CC=9      ←1
  │ llm                        145L  0C    3m  CC=10     ←3
  │ native                     143L  0C   13m  CC=6      ←1
  │ enrich                     141L  0C    4m  CC=14     ←1
  │ schemas                    137L  12C    0m  CC=0.0    ←0
  │ orchestrator               107L  0C    5m  CC=6      ←1
  │ logging_setup              100L  2C    6m  CC=3      ←0
  │ forms                       91L  0C    1m  CC=5      ←2
  │ prompt_catalog              82L  0C    1m  CC=8      ←0
  │ bootstrap                   78L  0C    3m  CC=14     ←0
  │ registry                    66L  0C    0m  CC=0.0    ←0
  │ loader                      62L  0C    3m  CC=5      ←1
  │ config                      60L  1C    0m  CC=0.0    ←0
  │ redis_store                 58L  1C    7m  CC=3      ←0
  │ observability               57L  0C    3m  CC=7      ←2
  │ intent                      55L  1C    2m  CC=3      ←0
  │ pyproject.toml              52L  0C    0m  CC=0.0    ←0
  │ resolve_mode                47L  0C    1m  CC=10     ←2
  │ factory                     46L  0C    1m  CC=4      ←1
  │ merge                       36L  0C    1m  CC=13     ←1
  │ system_executor             35L  0C   13m  CC=12     ←1
  │ pipeline                    31L  0C    1m  CC=6      ←2
  │ __init__                    30L  1C    4m  CC=1      ←0
  │ manifest.json               30L  0C    0m  CC=0.0    ←0
  │ delegate                    29L  0C    4m  CC=2      ←1
  │ memory                      23L  1C    5m  CC=1      ←0
  │ orchestrator                21L  0C    0m  CC=0.0    ←0
  │ facade                      19L  0C    1m  CC=2      ←0
  │ __init__                    17L  0C    0m  CC=0.0    ←0
  │ parser_enrich               15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  14L  0C    0m  CC=0.0    ←0
  │ __init__                    14L  0C    0m  CC=0.0    ←0
  │ __init__                    14L  0C    0m  CC=0.0    ←0
  │ __init__                    13L  0C    0m  CC=0.0    ←0
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
  │
  scripts/                        CC̄=3.5    ←in:0  →out:0
  │ aggregate-example-testql    49L  0C    1m  CC=7      ←0
  │ publish-all.sh              44L  0C    1m  CC=0.0    ←0
  │ setup-dev.sh                43L  0C    0m  CC=0.0    ←0
  │
  nlp2dsl_sdk/                    CC̄=3.2    ←in:34  →out:1
  │ !! client                     600L  2C   51m  CC=9      ←0
  │ !! artifacts                  410L  1C   17m  CC=17     ←7
  │ demos                      354L  1C   11m  CC=6      ←3
  │ cli                        228L  0C   10m  CC=13     ←0
  │ preview                    208L  0C    9m  CC=11     ←11
  │ encoding                    92L  0C    8m  CC=4      ←5
  │ __main__                    45L  0C    1m  CC=5      ←0
  │ example_loader              39L  0C    1m  CC=7      ←0
  │ __init__                    37L  0C    0m  CC=0.0    ←0
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
  backend/                        CC̄=2.2    ←in:0  →out:0
  │ engine                     269L  0C    7m  CC=11     ←2
  │ workflow                   199L  0C   10m  CC=8      ←0
  │ postgres                   172L  3C   11m  CC=4      ←0
  │ chat                       124L  0C    4m  CC=12     ←0
  │ logging_setup              100L  2C    6m  CC=3      ←5
  │ workflow_events             91L  2C    6m  CC=3      ←0
  │ settings                    81L  0C    7m  CC=2      ←0
  │ schemas                     64L  6C    0m  CC=0.0    ←0
  │ pyproject.toml              52L  0C    0m  CC=0.0    ←0
  │ __init__                    49L  1C    6m  CC=2      ←0
  │ main                        48L  0C    1m  CC=1      ←0
  │ config                      42L  1C    0m  CC=0.0    ←0
  │ memory                      37L  1C    6m  CC=2      ←0
  │ system                      29L  0C    1m  CC=2      ←0
  │ workflow                    22L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  11L  0C    0m  CC=0.0    ←0
  │ requirements.txt             9L  0C    0m  CC=0.0    ←0
  │ pytest.ini                   5L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  worker/                         CC̄=1.7    ←in:0  →out:0
  │ worker                     230L  0C   12m  CC=5      ←0
  │ logging_setup              100L  2C    6m  CC=3      ←0
  │ pyproject.toml              46L  0C    0m  CC=0.0    ←0
  │ config                      27L  1C    0m  CC=0.0    ←0
  │ Dockerfile                  11L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ requirements.txt             4L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1319L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  512L  0C    0m  CC=0.0    ←0
  │ nlp2dsl.yaml               186L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml         114L  0C    0m  CC=0.0    ←0
  │ Makefile                   102L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                82L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              63L  0C    0m  CC=0.0    ←0
  │ project.sh                  59L  0C    0m  CC=0.0    ←0
  │ metrun-profile.sh           48L  0C    0m  CC=0.0    ←0
  │ run-all-tests.sh            44L  0C    1m  CC=0.0    ←0
  │ pyqual.yaml                 41L  0C    0m  CC=0.0    ←0
  │ .pfix-test-wrapper.sh       16L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-examples.testql.toon.yaml   400L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml   128L  0C    0m  CC=0.0    ←0
  │ generated-api-smoke.testql.toon.yaml    39L  0C    0m  CC=0.0    ←0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     backend/app/__init__.py                   0L

COUPLING:
                                                             nlp2dsl_sdk                     nlp-service.app             packages.nlp2cmd-intent        examples.04-scheduled-report                 examples.01-invoice                   examples.02-email       examples.03-report-and-notify                 examples.12-ir-show  examples.08-multi-object-benchmark          examples.11-notify-quality                         backend.app                            examples      examples.07-email-conversation         examples.09-execution-smoke           examples.10-llm-benchmark
                         nlp2dsl_sdk                                  ──                                                                       1                                  ←5                                  ←4                                  ←4                                  ←4                                  ←4                                  ←2                                  ←3                                                                      ←2                                  ←2                                  ←2                                  ←1  hub
                     nlp-service.app                                                                      ──                                  ←5                                                                                                                                                                                                                                                                                              ←2                                                                                                                                                  hub
             packages.nlp2cmd-intent                                  ←1                                   5                                  ──                                                                                                                                                                                                                                                                                                                                                                                                                                                
        examples.04-scheduled-report                                   5                                                                                                          ──                                                                                                                                                                                                                                                                                                                                                                                                            
                 examples.01-invoice                                   4                                                                                                                                              ──                                                                                                                                                                                                                                                                                                                                                                        
                   examples.02-email                                   4                                                                                                                                                                                  ──                                                                                                                                                                                                                                                                                                                                    
       examples.03-report-and-notify                                   4                                                                                                                                                                                                                      ──                                                                                                                                                                                                                                                                                                
                 examples.12-ir-show                                   4                                                                                                                                                                                                                                                          ──                                                                                                                                                                                                                                                            
  examples.08-multi-object-benchmark                                   2                                                                                                                                                                                                                                                                                              ──                                                                                                                                                                                                                      ←1
          examples.11-notify-quality                                   3                                                                                                                                                                                                                                                                                                                                  ──                                                                                                                                                                                    
                         backend.app                                                                       2                                                                                                                                                                                                                                                                                                                                  ──                                                                                                                                                
                            examples                                   2                                                                                                                                                                                                                                                                                                                                                                                                          ──                                                                                                            
      examples.07-email-conversation                                   2                                                                                                                                                                                                                                                                                                                                                                                                                                              ──                                                                        
         examples.09-execution-smoke                                   2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  ──                                    
           examples.10-llm-benchmark                                   1                                                                                                                                                                                                                                                                                               1                                                                                                                                                                                                                      ──
  CYCLES: none
  HUB: nlp-service.app/ (fan-in=8)
  HUB: nlp2dsl_sdk/ (fan-in=34)

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 12 groups | 148f 13907L | 2026-06-05

SUMMARY:
  files_scanned: 148
  total_lines:   13907
  dup_groups:    12
  dup_fragments: 30
  saved_lines:   144
  scan_ms:       2797

HOTSPOTS[7] (files with most duplication):
  backend/app/logging_setup.py  dup=49L  groups=5  frags=5  (0.4%)
  nlp-service/app/logging_setup.py  dup=49L  groups=5  frags=5  (0.4%)
  worker/logging_setup.py  dup=49L  groups=5  frags=5  (0.4%)
  nlp-service/app/routing/parser/rules.py  dup=27L  groups=3  frags=5  (0.2%)
  backend/app/routers/settings.py  dup=24L  groups=2  frags=4  (0.2%)
  worker/worker.py  dup=22L  groups=1  frags=2  (0.2%)
  nlp-service/app/conversation/responses.py  dup=7L  groups=1  frags=1  (0.1%)

DUPLICATES[12] (ranked by impact):
  [5980042b45ef9ea3] ! STRU  setup_logging  L=22 N=3 saved=44 sim=1.00
      backend/app/logging_setup.py:79-100  (setup_logging)
      nlp-service/app/logging_setup.py:79-100  (setup_logging)
      worker/logging_setup.py:79-100  (setup_logging)
  [a58ac04d8adce867]   EXAC  format  L=12 N=3 saved=24 sim=1.00
      backend/app/logging_setup.py:40-51  (format)
      nlp-service/app/logging_setup.py:40-51  (format)
      worker/logging_setup.py:40-51  (format)
  [ffd95d6b2707ba43]   EXAC  dispatch  L=9 N=3 saved=18 sim=1.00
      backend/app/logging_setup.py:68-76  (dispatch)
      nlp-service/app/logging_setup.py:68-76  (dispatch)
      worker/logging_setup.py:68-76  (dispatch)
  [fe1a465464777068]   STRU  handle_notify_slack  L=11 N=2 saved=11 sim=1.00
      worker/worker.py:119-129  (handle_notify_slack)
      worker/worker.py:133-143  (handle_notify_telegram)
  [8e33482aef8974e1]   STRU  action_schema  L=7 N=2 saved=7 sim=1.00
      backend/app/routers/settings.py:29-35  (action_schema)
      backend/app/routers/settings.py:47-53  (get_settings_section)
  [8aa06fa5f1348ed4]   STRU  _execute_keyword_in_text  L=7 N=2 saved=7 sim=1.00
      nlp-service/app/conversation/responses.py:54-60  (_execute_keyword_in_text)
      nlp-service/app/routing/parser/rules.py:240-246  (_alias_in_text)
  [e2bd3c5d1f7d650b]   EXAC  __init__  L=3 N=3 saved=6 sim=1.00
      backend/app/logging_setup.py:36-38  (__init__)
      nlp-service/app/logging_setup.py:36-38  (__init__)
      worker/logging_setup.py:36-38  (__init__)
  [2283cb9d4d16ec25]   EXAC  __init__  L=3 N=3 saved=6 sim=1.00
      backend/app/logging_setup.py:64-66  (__init__)
      nlp-service/app/logging_setup.py:64-66  (__init__)
      worker/logging_setup.py:64-66  (__init__)
  [8af82767bfb2b892]   STRU  run_workflow_endpoint  L=3 N=3 saved=6 sim=1.00
      backend/app/routers/workflow.py:77-79  (run_workflow_endpoint)
      backend/app/routers/workflow.py:83-85  (start_workflow_endpoint)
      nlp-service/app/main.py:94-99  (parse_text)
  [d8abcb97f9e3aea3]   STRU  _extract_report_type  L=6 N=2 saved=6 sim=1.00
      nlp-service/app/routing/parser/rules.py:424-429  (_extract_report_type)
      nlp-service/app/routing/parser/rules.py:432-437  (_extract_format)
  [2ce1096adac6d1a4]   STRU  actions_schema  L=5 N=2 saved=5 sim=1.00
      backend/app/routers/settings.py:21-25  (actions_schema)
      backend/app/routers/settings.py:39-43  (get_settings)
  [88c3564ed3834adc]   STRU  _extract_file_path_entity  L=4 N=2 saved=4 sim=1.00
      nlp-service/app/routing/parser/rules.py:502-505  (_extract_file_path_entity)
      nlp-service/app/routing/parser/rules.py:508-511  (_extract_setting_path_entity)

REFACTOR[12] (ranked by priority):
  [1] ● extract_function   → utils/setup_logging.py
      WHY: 3 occurrences of 22-line block across 3 files — saves 44 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [2] ● extract_class      → utils/format.py
      WHY: 3 occurrences of 12-line block across 3 files — saves 24 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [3] ● extract_class      → utils/dispatch.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [4] ○ extract_function   → worker/utils/handle_notify_slack.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: worker/worker.py
  [5] ○ extract_function   → backend/app/routers/utils/action_schema.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: backend/app/routers/settings.py
  [6] ○ extract_function   → nlp-service/app/utils/_execute_keyword_in_text.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: nlp-service/app/conversation/responses.py, nlp-service/app/routing/parser/rules.py
  [7] ● extract_class      → utils/__init__.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [8] ● extract_class      → utils/__init__.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: backend/app/logging_setup.py, nlp-service/app/logging_setup.py, worker/logging_setup.py
  [9] ○ extract_function   → utils/run_workflow_endpoint.py
      WHY: 3 occurrences of 3-line block across 2 files — saves 6 lines
      FILES: backend/app/routers/workflow.py, nlp-service/app/main.py
  [10] ○ extract_function   → nlp-service/app/routing/parser/utils/_extract_report_type.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: nlp-service/app/routing/parser/rules.py
  [11] ○ extract_function   → backend/app/routers/utils/actions_schema.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: backend/app/routers/settings.py
  [12] ○ extract_function   → nlp-service/app/routing/parser/utils/_extract_file_path_entity.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: nlp-service/app/routing/parser/rules.py

QUICK_WINS[5] (low risk, high savings — do first):
  [4] extract_function   saved=11L  → worker/utils/handle_notify_slack.py
      FILES: worker.py
  [5] extract_function   saved=7L  → backend/app/routers/utils/action_schema.py
      FILES: settings.py
  [6] extract_function   saved=7L  → nlp-service/app/utils/_execute_keyword_in_text.py
      FILES: responses.py, rules.py
  [9] extract_function   saved=6L  → utils/run_workflow_endpoint.py
      FILES: workflow.py, main.py
  [10] extract_function   saved=6L  → nlp-service/app/routing/parser/utils/_extract_report_type.py
      FILES: rules.py

DEPENDENCY_RISK[6] (duplicates spanning multiple packages):
  setup_logging  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
  format  packages=3  files=3
      backend/app/logging_setup.py
      nlp-service/app/logging_setup.py
      worker/logging_setup.py
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
  run_workflow_endpoint  packages=2  files=2
      backend/app/routers/workflow.py
      nlp-service/app/main.py

EFFORT_ESTIMATE (total ≈ 8.3h):
  hard   setup_logging                       saved=44L  ~176min
  hard   format                              saved=24L  ~96min
  medium dispatch                            saved=18L  ~72min
  easy   handle_notify_slack                 saved=11L  ~22min
  easy   action_schema                       saved=7L  ~14min
  easy   _execute_keyword_in_text            saved=7L  ~14min
  easy   __init__                            saved=6L  ~24min
  easy   __init__                            saved=6L  ~24min
  easy   run_workflow_endpoint               saved=6L  ~24min
  easy   _extract_report_type                saved=6L  ~12min
  ... +2 more (~18min)

METRICS-TARGET:
  dup_groups:  12 → 0
  saved_lines: 144 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 542 func | 82f | 2026-06-05
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py
      WHY: 1209L, 2 classes, max CC=73
      EFFORT: ~4h  IMPACT: 88257

  [2] !! SPLIT-FUNC      KeywordIntentDetector._fast_path_detection  CC=73  fan=29
      WHY: CC=73 exceeds 15
      EFFORT: ~1h  IMPACT: 2117

  [3] !! SPLIT-FUNC      KeywordPatterns._load_detector_config_from_json  CC=33  fan=18
      WHY: CC=33 exceeds 15
      EFFORT: ~1h  IMPACT: 594

  [4] !  SPLIT-FUNC      resolve_intent  CC=18  fan=19
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 342

  [5] !  SPLIT-FUNC      KeywordPatterns._load_patterns_from_json  CC=19  fan=17
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 323

  [6] !  SPLIT-FUNC      _build_config  CC=19  fan=16
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 304

  [7] !  SPLIT-FUNC      KeywordIntentDetector.detect  CC=17  fan=17
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 289

  [8] !  SPLIT-FUNC      orient_query  CC=16  fan=16
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 256

  [9] !  SPLIT-FUNC      _resolve_file_list_host_command  CC=15  fan=17
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 255

  [10] !  SPLIT-FUNC      KeywordIntentDetector._keyword_detection  CC=15  fan=12
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 180


RISKS[3]:
  ⚠ Splitting packages/nlp2cmd-intent/src/nlp2cmd_intent/data/patterns.json may break 0 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths
  ⚠ Splitting packages/nlp2cmd-intent/src/nlp2cmd_intent/keywords/keyword_detector.py may break 22 import paths

METRICS-TARGET:
  CC̄:          3.6 → ≤2.5
  max-CC:      73 → ≤20
  god-modules: 7 → 0
  high-CC(≥15): 12 → ≤6
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
  prev CC̄=3.6 → now CC̄=3.6
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
