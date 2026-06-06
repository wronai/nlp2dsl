# Dokumentacja nlp2dsl

Indeks dokumentacji platformy MVP (NLP → DSL → CMD → Docker).

## Szybki start

| Temat | Dokument |
|-------|----------|
| Instalacja, porty, conversation API | [README główny](../README.md) |
| Przykłady i scenariusze | [examples/README.md](../examples/README.md) |
| Aktualny stan przykładów 01-14 i publish layer | [system-status-examples-01-14.md](system-status-examples-01-14.md) |
| Przykład faktury (autonomiczny) | [examples/01-invoice/README.md](../examples/01-invoice/README.md) |

## Architektura i mapa systemu

| Dokument | Opis |
|----------|------|
| [doql-system-map.md](doql-system-map.md) | `environment.doql.less` — runtimes, commands, conversation |
| [doql-runtimes.md](doql-runtimes.md) | RuntimeSpec, dispatch, health |
| [doql-dynamic-generation.md](doql-dynamic-generation.md) | SystemMapIR, generowanie mapy LLM |
| [process-agent.md](process-agent.md) | ProcessAgent, preflight, self-resolve |
| [architecture-routing-refactor.md](architecture-routing-refactor.md) | Routing intentów, governance |

## Walidacja i refleksja

| Dokument | Opis |
|----------|------|
| [validation.md](validation.md) | **Walidacja requestu** — fazy, PDF, autonomiczna naprawa |
| [reflection-model.md](reflection-model.md) | ReflectionReport, pętla model → decyzja → refleksja |
| [artifacts.md](artifacts.md) | `.nlp2dsl/` — pipeline, DOQL, załączniki |

## Integracje i rozszerzenia

| Dokument | Opis |
|----------|------|
| [intract-integration.md](intract-integration.md) | Kontrakty planu, Intract gate |
| [access-control.md](access-control.md) | ACL, resource_areas, agenci |
| [autonomous-stack.md](autonomous-stack.md) | Stack cron + compose (przykład 13) |
| [encoding.md](encoding.md) | UTF-8, polskie znaki w CLI/SDK |

## Refaktoryzacja i migracja

| Dokument | Opis |
|----------|------|
| [REFACTOR-PLAN.md](REFACTOR-PLAN.md) | Plan refaktoryzacji (Mullm, moduły, walidacja) |
| [migration-persistence.md](migration-persistence.md) | Postgres, Redis, historia workflow |

## Pakiety SDK i IR

| Dokument | Opis |
|----------|------|
| [packages/README.md](../packages/README.md) | Indeks wszystkich pakietów w `packages/` |
| [packages/dsl-contracts/README.md](../packages/dsl-contracts/README.md) | Kontrakty akcji, drafty |
| [packages/dsl-validate/README.md](../packages/dsl-validate/README.md) | Pipeline walidacji |
| [packages/nlp2dsl-artifacts/README.md](../packages/nlp2dsl-artifacts/README.md) | Artefakty `.nlp2dsl/` |
| [packages/workflow-export/README.md](../packages/workflow-export/README.md) | Eksport markpact + pactown |
| [packages/nlp2dsl-stack/README.md](../packages/nlp2dsl-stack/README.md) | Compose stack + cron |
| [packages/testql-conversations/README.md](../packages/testql-conversations/README.md) | Scenariusze TestTOON |
| [env2llm](../../../semcod/env2llm/README.md) | Mapa środowiska DOQL (repo semcod) |

Pakiety IR (nlp2cmd): `pact-ir`, `nlp2cmd-intent`, `nlp2cmd-planner`, `nlp2cmd-propact`, `nlp2dsl-show` — szczegóły w [packages/README.md](../packages/README.md).

## Porty Docker (domyślne)

| Serwis | Host | Uwagi |
|--------|------|-------|
| Backend | `:8010` | Gateway, chat, workflow |
| NLP Service | `:8012` | Conversation, voice UI `/chat` |
| Worker | `:8004` | Executory akcji |

SDK czeka na `/health` wszystkich trzech (`NLP2DSL_HEALTH_TIMEOUT`, domyślnie 120 s).
