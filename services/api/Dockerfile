FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Copy the shared module to match the path referenced in pyproject.toml
COPY shared/ /home/nikos/home-telemetry/shared/

# Copy the api service
COPY services/api/ .

# Install dependencies (skip dev extras)
RUN poetry install --without dev

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
