FROM python:3.11-slim

# Install redis-cli for healthchecks and procps for process management (kill)
RUN apt-get update && apt-get install -y redis-tools procps && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry for dependency management
RUN pip install --no-cache-dir poetry

# Copy shared code
COPY shared /shared

# Copy notifier service files
COPY services/notifier/pyproject.toml /app/
COPY services/notifier/app ./app

# Set Python path
ENV PYTHONPATH="/:/shared"

# Install dependencies from pyproject.toml
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only=main

CMD ["python", "app/main.py"]
