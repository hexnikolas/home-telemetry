FROM python:3.12-slim

RUN pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app

# Copy entire repo maintaining directory structure
COPY . /app/

WORKDIR /app

# Install shared first
RUN cd shared && poetry install --without dev

# Install ingestion service
RUN cd services/ingestion && poetry install --without dev

WORKDIR /app/services/ingestion

# Run the worker
CMD ["python", "-m", "app.worker"]
