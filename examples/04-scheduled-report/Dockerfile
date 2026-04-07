# Dockerfile dla przykładu zaplanowanych raportów
# Demonstruje integrację z systemem schedulowania i storage

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY README.md pyproject.toml ./
COPY nlp2dsl_sdk ./nlp2dsl_sdk
RUN pip install --no-cache-dir .

# Kopiuj kod przykładu
COPY examples/04-scheduled-report/main.py ./examples/04-scheduled-report/main.py
COPY examples/04-scheduled-report/run.sh ./examples/04-scheduled-report/run.sh

# Uprawnienia dla skryptu
RUN chmod +x ./examples/04-scheduled-report/run.sh

WORKDIR /app/examples/04-scheduled-report

# Domyślne polecenie
CMD ["python3", "main.py"]
