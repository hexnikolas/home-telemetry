FROM python:3.13-slim

RUN pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app

# Copy entire repo maintaining directory structure
COPY . /app/

WORKDIR /app

# Install shared first
RUN cd shared && poetry install --without dev

# Install API service
RUN cd services/api && poetry install --without dev

WORKDIR /app/services/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
