# Dockerfile dla przykładu raportów i powiadomień
# Demonstruje integrację z Slack i generowanie raportów

FROM python:3.11-slim

WORKDIR /app

# Zależności
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiuj kod przykładu
COPY main.py .
COPY run.sh .

# Uprawnienia dla skryptu
RUN chmod +x run.sh

# Domyślne polecenie
CMD ["python3", "main.py"]
