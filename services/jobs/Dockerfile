FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --no-dev

# Copy application code
COPY app/ app/

# Default to worker, can be overridden for scheduler
CMD ["python", "-m", "app.worker"]
