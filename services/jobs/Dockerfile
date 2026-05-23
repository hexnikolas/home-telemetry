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

# Run Dramatiq worker with scheduler (1 process, 4 threads each)
CMD ["python", "-m", "dramatiq", "app.worker", "-p", "1", "-t", "4"]
