FROM python:3.11-slim

WORKDIR /app 

COPY requirements /app/requirements
RUN pip install --no-cache-dir -U pip \ 
    && pip install --no-cache-dir -r /app/requirements/worker.txt

COPY apps/worker/worker /app/worker
COPY packages /app/packages

ENV PYTHONPATH=/app

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]