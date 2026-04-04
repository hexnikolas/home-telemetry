FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Copy the shared module to match the path referenced in pyproject.toml
COPY shared/ /home/nikos/home-telemetry/shared/

# Copy dependency files
COPY services/jobs/pyproject.toml services/jobs/poetry.lock* ./

# Remove lock file so poetry resolves paths fresh from pyproject.toml
RUN rm -f poetry.lock && poetry install --only main

# Copy application code
COPY services/jobs/app/ app/

# Run arq worker with built-in scheduler and cron job support
CMD ["arq", "app.worker.WorkerSettings"]
