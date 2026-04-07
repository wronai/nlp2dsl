# MVP Automation Platform — Konwersacyjny AI Kompilujący Język Naturalny do Workflow

**Status projektu:** MVP+ z Conversation Loop | **Język:** Python (FastAPI) | **Infrastruktura:** Docker Compose

---

MVP Automation Platform to system kompilujący intencje biznesowe wyrażone językiem naturalnym do wykonywalnych procesów w kontenerach Docker. Użytkownik prowadzi dialog z AI, system dopytuje o brakujące dane, generuje dynamiczny formularz UI i buduje workflow — wszystko bez pisania kodu.

## Kluczowa zasada

LLM rozumie język → Pydantic waliduje → deterministyczny Mapper buduje DSL → Docker wykonuje. LLM nigdy nie generuje finalnego DSL bezpośrednio, co gwarantuje przewidywalność, debugowalność i kontrolę nad procesem.

## Conversation Loop — dialog AI → DSL

System nie wymaga kompletnego opisu w jednej wiadomości. Użytkownik może napisać "chcę wysłać fakturę" i system przeprowadzi wieloturowy dialog dopytując o kwotę, walutę i adres odbiorcy. Stan konwersacji jest akumulowany — każda odpowiedź użytkownika uzupełnia brakujące dane aż workflow będzie kompletny.

Gdy użytkownik poda wystarczające informacje, system prezentuje gotowy DSL workflow i czeka na komendę „uruchom" aby go wykonać w kontenerach Docker.

## Schema-driven UI — backend generuje formularze

Zamiast ręcznie budować formularze dla każdej akcji, backend generuje schematy UI dynamicznie z rejestru akcji. Każde pole ma typ (number, email, select), etykietę, opcje i flagę wymagalności. Frontend renderuje formularze automatycznie z tych schematów.

Gdy w dialogu brakuje danych, system zwraca zarówno tekstowe pytanie (dla trybu chat/voice) jak i schemat formularza (dla trybu GUI) — hybryda pozwalająca użytkownikowi wybrać wygodniejszy tryb interakcji.

## Pipeline NLP → DSL → Execution

NLP Service obsługuje trzy izolowane etapy. Parser (regułowy offline lub LLM) rozpoznaje intencję i wyodrębnia encje. Deterministyczny mapper buduje formalny DSL na podstawie rejestru akcji. Orchestrator zarządza stanem konwersacji i prowadzi dialog.

Parser regułowy działa offline bez API, rozpoznaje polskie i angielskie komendy, wykrywa kwoty z walutami, adresy email, kanały Slack i harmonogramy. Automatycznie łączy wiele akcji w composite intents.

## Architektura kontenerowa

Trzy mikroserwisy: NLP Service (port 8002), Backend/API Gateway (port 8000) i Worker (port 8001). Postgres i Redis zapewniają persystencję. Całość uruchamia się jednym `docker compose up --build`.

## Planowane rozszerzenia

Multi-agent architecture z wyspecjalizowanymi agentami (Intent, Entity, Planner, Validator). React Live UI z czatem i wizualizacją DAG workflow w czasie rzeczywistym. Event-driven komunikacja przez Redis Streams. Multi-tenant SaaS z auth, billing i quotas.