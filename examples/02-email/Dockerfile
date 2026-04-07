# Dockerfile dla przykładu wysyłania e-maili
# Demonstruje integrację z SMTP

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY README.md pyproject.toml ./
COPY nlp2dsl_sdk ./nlp2dsl_sdk
RUN pip install --no-cache-dir .

# Kopiuj kod przykładu
COPY examples/02-email/main.py ./examples/02-email/main.py
COPY examples/02-email/run.sh ./examples/02-email/run.sh

# Uprawnienia dla skryptu
RUN chmod +x ./examples/02-email/run.sh

WORKDIR /app/examples/02-email

# Domyślne polecenie
CMD ["python3", "main.py"]
