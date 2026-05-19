FROM python:3.11-slim

# Install redis-cli for healthchecks and procps for process management (kill)
RUN apt-get update && apt-get install -y redis-tools procps && rm -rf /var/lib/apt/lists/*

# Install poetry for dependency management
RUN pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app

# Copy entire repo maintaining directory structure
COPY . /app/

WORKDIR /app

# Install shared first
RUN cd shared && poetry install --without dev

# Install notifier service
RUN cd services/notifier && poetry install

WORKDIR /app/services/notifier

CMD ["python", "app/main.py"]
