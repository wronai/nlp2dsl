# Dokumentacja nlp2dsl

Indeks dokumentacji platformy MVP (NLP → DSL → CMD → Docker).

## Szybki start

| Temat | Dokument |
|-------|----------|
| Instalacja, porty, conversation API | [README główny](../README.md) |
| Przykłady i scenariusze | [examples/README.md](../examples/README.md) |
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

## Pakiety IR (nlp2cmd)

| Dokument | Opis |
|----------|------|
| [packages/README.md](../packages/README.md) | IntentIR, ExecutionPlanIR, nlp2cmd plan |

## Porty Docker (domyślne)

| Serwis | Host | Uwagi |
|--------|------|-------|
| Backend | `:8010` | Gateway, chat, workflow |
| NLP Service | `:8012` | Conversation, voice UI `/chat` |
| Worker | `:8004` | Executory akcji |

SDK czeka na `/health` wszystkich trzech (`NLP2DSL_HEALTH_TIMEOUT`, domyślnie 120 s).
