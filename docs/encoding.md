# Kodowanie UTF-8 (polskie znaki)

## Automatyczna konfiguracja

Od SDK **0.1.11** nie trzeba ręcznie ustawiać `LANG` ani `PYTHONIOENCODING`.

Przy imporcie `nlp2dsl_sdk` (lub starcie CLI) uruchamia się `configure_utf8()`:

- `stdout` / `stderr` / `stdin` → UTF-8 (`errors=replace`)
- gdy locale jest ASCII (`C`, `POSIX`, brak `UTF-8` w `LANG`) → `C.UTF-8`
- `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`

Dotyczy:

| Wejście | Mechanizm |
|---------|-----------|
| `nlp2dsl`, `nlp2dsl-demo` | `cli.py` + import SDK |
| `nlp2dsl-show` | `nlp2dsl_show.encoding` (deleguje do SDK gdy zainstalowany) |
| `examples/*/main.py` | import `nlp2dsl_sdk` w `scenario.py` |
| `examples/run-all.sh` | nadal ustawia UTF-8 w shellu (opcjonalne, dla subprocessów) |

## Wyłączenie

```bash
NLP2DSL_UTF8=0 nlp2dsl run "Wyślij email do a@b.pl"
```

## Ręczna konfiguracja (rzadko potrzebna)

Tylko gdy auto-konfiguracja jest wyłączona lub terminal jest bardzo stary:

```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8
```

## Objawy złego kodowania

| Widać | Powinno być |
|-------|-------------|
| `znajd?` | `znajdź` |
| `Przyk?ad` | `Przykład` |
| `krokw` | `kroków` |

Jeśli po aktualizacji SDK problem zostaje, sprawdź font/terminal (np. `echo $LANG`) i ewentualnie `NLP2DSL_UTF8=1` (domyślnie włączone).
