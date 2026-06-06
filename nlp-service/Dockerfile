FROM python:3.11-slim

WORKDIR /app

COPY nlp-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY nlp2dsl_sdk/ /app/nlp2dsl_sdk/
COPY nlp-service/app/ app/
COPY nlp-service/integrations/ integrations/

ENV PYTHONPATH=/app

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
