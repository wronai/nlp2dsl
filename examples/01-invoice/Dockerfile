# Dockerfile dla przykładu wysyłania faktur
# Demonstruje integrację z prawdziwym serwisem SMTP

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY README.md pyproject.toml ./
COPY nlp2dsl_sdk ./nlp2dsl_sdk
RUN pip install --no-cache-dir .

# Kopiuj kod przykładu
COPY examples/01-invoice/main.py ./examples/01-invoice/main.py
COPY examples/01-invoice/run.sh ./examples/01-invoice/run.sh

# Uprawnienia dla skryptu
RUN chmod +x ./examples/01-invoice/run.sh

WORKDIR /app/examples/01-invoice

# Domyślne polecenie
CMD ["python3", "main.py"]
