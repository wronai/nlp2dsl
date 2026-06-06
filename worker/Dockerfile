FROM python:3.11-slim

WORKDIR /app

COPY worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY nlp2dsl_sdk/ /app/nlp2dsl_sdk/
COPY worker/worker.py worker/logging_setup.py worker/config.py worker/invoice_pdf.py worker/path_resolve.py worker/attachment_validation.py worker/action_catalog.py worker/step_validator.py worker/registry.py ./

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8000"]
