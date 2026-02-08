FROM python:3.11-slim

WORKDIR /app

COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r /app/requirements/telegram_bot.txt

COPY apps/telegram_bot/bot /app/bot

ENV PYTHONPATH=/app

CMD ["python", "-m", "bot.main"]
