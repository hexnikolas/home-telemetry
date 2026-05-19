FROM python:3.13-slim

# Install Poetry
RUN pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app

# Copy entire repo maintaining directory structure
COPY . /app/

WORKDIR /app

# Install shared first
RUN cd shared && poetry install --without dev

# Install jobs service
RUN cd services/jobs && poetry install

WORKDIR /app/services/jobs

# Run arq worker with built-in scheduler and cron job support
CMD ["arq", "app.worker.WorkerSettings"]
