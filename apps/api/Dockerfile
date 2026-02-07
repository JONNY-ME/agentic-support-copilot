FROM python:3.11-slim

WORKDIR /app

COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r /app/requirements/api.txt

COPY apps/api/app /app/app
COPY apps/api/alembic /app/alembic
COPY apps/api/alembic.ini /app/alembic.ini
COPY packages /app/packages
COPY scripts /app/scripts

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
