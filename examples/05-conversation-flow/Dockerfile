# Dockerfile dla przykładu konwersacyjnego flow
# Demonstruje integrację z API i zarządzanie stanem

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY README.md pyproject.toml ./
COPY nlp2dsl_sdk ./nlp2dsl_sdk
RUN pip install --no-cache-dir .

# Kopiuj kod przykładu
COPY examples/05-conversation-flow/main.py ./examples/05-conversation-flow/main.py
COPY examples/05-conversation-flow/run.sh ./examples/05-conversation-flow/run.sh

# Uprawnienia dla skryptu
RUN chmod +x ./examples/05-conversation-flow/run.sh

WORKDIR /app/examples/05-conversation-flow

# Domyślne polecenie
CMD ["python3", "main.py"]
