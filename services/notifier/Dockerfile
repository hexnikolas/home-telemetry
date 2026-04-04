FROM python:3.11-slim

# Install redis-cli for healthchecks and procps for process management (kill)
RUN apt-get update && apt-get install -y redis-tools procps && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry for dependency management
RUN pip install --no-cache-dir poetry

# Copy shared code to match the path referenced in pyproject.toml
COPY shared/ /home/nikos/home-telemetry/shared/

# Copy notifier service files
COPY services/notifier/ .

ENV PYTHONPATH="/:/shared"

# Remove lock file so poetry resolves paths fresh from pyproject.toml
# (lock file has the host machine's path for the local shared package)
RUN rm -f poetry.lock && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only=main

CMD ["python", "app/main.py"]
