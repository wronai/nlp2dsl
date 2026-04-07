# Dockerfile dla przykładu raportów i powiadomień
# Demonstruje integrację z Slack i generowanie raportów

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY README.md pyproject.toml ./
COPY nlp2dsl_sdk ./nlp2dsl_sdk
RUN pip install --no-cache-dir .

# Kopiuj kod przykładu
COPY examples/03-report-and-notify/main.py ./examples/03-report-and-notify/main.py
COPY examples/03-report-and-notify/run.sh ./examples/03-report-and-notify/run.sh

# Uprawnienia dla skryptu
RUN chmod +x ./examples/03-report-and-notify/run.sh

WORKDIR /app/examples/03-report-and-notify

# Domyślne polecenie
CMD ["python3", "main.py"]
